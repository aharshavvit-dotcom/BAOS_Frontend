"""
Recommender — Decision Engine Layer 3
Real-time berth recommendation using trained ML models + CP-SAT validation.

Phase 3 Enhancements:
  - Uncertainty-aware ranking (P25/P50/P75 from quantile regression)
  - Data quality tags from ConstraintLibrary
  - Spec-backed pros/cons with provenance markers
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.db.repositories.port_store import (
    load_port_config, get_models_dir, is_trained, load_history,
)
from engines.learning.training.feature_builder import build_inference_features
from engines.learning.training.ml_models import (
    ServiceTimePredictor, BerthSuitabilityModel,
    DelayPredictor, DecisionRanker, BerthOption, QuantilePrediction,
)


def recommend_berth(
    vessel: dict,
    port_name: str,
    top_k: int = 3,
) -> List[BerthOption]:
    """
    Full recommendation pipeline:
    1. Load port config + trained models
    2. Build inference features for all berths
    3. ML models predict: suitability, service time, delay (with uncertainty)
    4. Decision ranker combines scores (penalizes high uncertainty)
    5. Generate pros/cons with provenance tags
    Returns top-k BerthOption objects.
    """
    if not is_trained(port_name):
        raise RuntimeError(f"Port '{port_name}' has no trained models. Run training first.")

    # Load
    port_config = load_port_config(port_name)
    models_dir = get_models_dir(port_name)

    bsm = BerthSuitabilityModel.load(models_dir / "berth_suitability.pkl")
    stp = ServiceTimePredictor.load(models_dir / "service_time.pkl")
    dp = DelayPredictor.load(models_dir / "delay_predictor.pkl")
    dr = DecisionRanker.load(models_dir / "decision_ranker.pkl")

    # Load feature columns for alignment
    feat_cols_path = models_dir / "feature_columns.json"
    if feat_cols_path.exists():
        with open(feat_cols_path) as f:
            train_cols = json.load(f)
    else:
        train_cols = None

    berths = port_config.get("berths", [])
    berth_info_map = {str(b["berth_code"]): b for b in berths}

    # --- Data-Driven Feasibility Filtering ---
    constraint_lib = None
    try:
        from engines.ingestion.spec_ingest import build_port_master
        from engines.simulation.optimization.constraint_library import ConstraintLibrary

        sample_data = _ROOT / "sample_data"
        berth_cfg_path = sample_data / "Berth_configurations.xlsx"
        ops_cap_path = sample_data / "Operational_Capability_of_Berth.xlsx"

        if berth_cfg_path.exists():
            port_master = build_port_master(
                port_name=port_name,
                berth_config_path=str(berth_cfg_path),
                operational_capability_path=str(ops_cap_path) if ops_cap_path.exists() else None,
            )
            constraint_lib = ConstraintLibrary(port_master)
    except Exception:
        constraint_lib = None

    vessel_loa = float(vessel.get("loa", 0))
    vessel_beam = float(vessel.get("beam", 0))
    vessel_draft = float(vessel.get("draft", vessel.get("adraft", 0)))
    vessel_type = vessel.get("vessel_type", "")
    cargo_type = vessel.get("cargo_type", "")

    eligible_berths = {}
    # Track rejection reasons for every berth that fails
    rejection_reasons: Dict[str, List[str]] = {}

    vessel_dict = {
        "vessel_id": vessel.get("name", "input"),
        "loa": vessel_loa,
        "draft": vessel_draft,
        "beam": vessel_beam,
        "dwt": float(vessel.get("dwt", 0)),
        "vessel_type": vessel_type,
        "cargo_category": cargo_type,
    }

    for bc, bi in berth_info_map.items():
        if constraint_lib and str(bc) in constraint_lib.port.berths:
            feas_result = constraint_lib.check_feasibility(vessel_dict, bc)
            if feas_result.feasible:
                score = constraint_lib.compute_suitability_score(vessel_dict, bc)
                bi["_compat_score"] = score
                bi["_data_quality"] = feas_result.data_quality.value
                bi["_feas_result"] = feas_result  # Store for confidence calc
                eligible_berths[bc] = bi
            else:
                # Collect specific rejection reasons
                reasons = []
                for cr in feas_result.constraint_results:
                    if not cr.passed:
                        reasons.append(cr.reason)
                rejection_reasons[bc] = reasons if reasons else [feas_result.explanation or "Hard constraint violated"]
        else:
            from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score
            fail_reasons = []

            if vessel_loa > 0 and bi.get("max_loa_m", 999) < vessel_loa:
                fail_reasons.append(
                    f"LOA {vessel_loa:.0f}m exceeds max {bi.get('max_loa_m', 999):.0f}m"
                )
            if vessel_loa > 0 and bi.get("min_loa_m", 0) > 0 and vessel_loa < bi.get("min_loa_m", 0):
                fail_reasons.append(
                    f"LOA {vessel_loa:.0f}m below minimum {bi.get('min_loa_m', 0):.0f}m"
                )
            if vessel_beam > 0 and bi.get("max_beam_m", 999) < vessel_beam:
                fail_reasons.append(
                    f"Beam {vessel_beam:.0f}m exceeds max {bi.get('max_beam_m', 999):.0f}m"
                )
            if vessel_draft > 0 and bi.get("max_draft_m", 20) < vessel_draft:
                fail_reasons.append(
                    f"Draft {vessel_draft:.1f}m exceeds max {bi.get('max_draft_m', 20):.1f}m"
                )

            if fail_reasons:
                rejection_reasons[bc] = fail_reasons
                continue

            equipment_types = bi.get("equipment_types", bi.get("equipment", []))
            allowed_vessel_types = bi.get("allowed_vessel_types", [])
            compat_score, _, _ = compute_compatibility_score(
                vessel_type, cargo_type, equipment_types, allowed_vessel_types
            )

            if compat_score >= 30:
                bi["_compat_score"] = compat_score
                bi["_data_quality"] = "QualityGate.RED" if constraint_lib else "QualityGate.YELLOW"
                eligible_berths[bc] = bi
            else:
                rejection_reasons[bc] = [
                    f"Low vessel-berth compatibility ({compat_score:.0f}%): "
                    f"vessel type '{vessel_type}' not well-matched with "
                    f"allowed types {allowed_vessel_types}"
                ]

    if not eligible_berths:
        # Build detailed per-berth rejection explanation
        rejection_lines = []
        for bc, reasons in rejection_reasons.items():
            bi = berth_info_map.get(bc, {})
            bname = bi.get("berth_name", bc)
            reason_str = "; ".join(reasons)
            rejection_lines.append(f"• {bname} ({bc}): {reason_str}")

        if not rejection_lines:
            rejection_lines.append("No berths available for analysis")

        detail_text = "\n".join(rejection_lines)
        summary = (
            f"For the given vessel configuration (LOA={vessel_loa:.0f}m, "
            f"Beam={vessel_beam:.0f}m, Draft={vessel_draft:.1f}m, "
            f"Type={vessel_type}, Cargo={cargo_type}), "
            f"no berth can be assigned. "
            f"Rejection details for each berth:\n{detail_text}"
        )

        return [BerthOption(
            berth_code="NONE", berth_name="No eligible berth",
            rank=0, confidence=0,
            explanation=summary,
            cons=rejection_lines[:10],  # Top 10 rejection lines
        )]

    # Compute congestion level
    try:
        df_hist = load_history(port_name)
        congestion = len(df_hist) // max(df_hist["berthcode"].nunique() if "berthcode" in df_hist.columns else 1, 1)
        congestion = min(congestion, 20)
    except Exception:
        congestion = 5

    # Build feature vectors for each eligible berth
    suitability_scores = {}
    wait_predictions = {}
    service_predictions = {}
    # Phase 3: Uncertainty data
    service_uncertainty: Dict[str, QuantilePrediction] = {}
    delay_uncertainty: Dict[str, QuantilePrediction] = {}

    for bc, bi in eligible_berths.items():
        feat = build_inference_features(vessel, bi, port_config, congestion)

        # Align features with training columns
        if train_cols:
            for c in train_cols:
                if c not in feat.columns:
                    feat[c] = 0
            feat = feat[train_cols]

        # Predict service time WITH uncertainty
        try:
            svc_quant = stp.predict_with_uncertainty(feat)
            svc = svc_quant[0].point
            service_uncertainty[bc] = svc_quant[0]
        except Exception:
            svc = 12.0
            service_uncertainty[bc] = QuantilePrediction(
                point=12.0, lower=8.0, upper=18.0, confidence_width=10.0
            )
        service_predictions[bc] = svc

        # Predict delay WITH uncertainty
        try:
            dly_quant = dp.predict_with_uncertainty(feat)
            delay = dly_quant[0].point
            delay_uncertainty[bc] = dly_quant[0]
        except Exception:
            delay = 3.0
            delay_uncertainty[bc] = QuantilePrediction(
                point=3.0, lower=1.0, upper=6.0, confidence_width=5.0
            )
        wait_predictions[bc] = delay

    # Get suitability scores from classifier
    first_berth = list(eligible_berths.values())[0]
    base_feat = build_inference_features(vessel, first_berth, port_config, congestion)
    if train_cols:
        for c in train_cols:
            if c not in base_feat.columns:
                base_feat[c] = 0
        base_feat = base_feat[train_cols]

    try:
        top_predictions = bsm.predict_top_k(base_feat, k=len(eligible_berths))
        for bc_code, prob in top_predictions:
            if bc_code in eligible_berths:
                suitability_scores[bc_code] = prob
    except Exception:
        for bc in eligible_berths:
            suitability_scores[bc] = 1.0 / len(eligible_berths)

    # Ensure all eligible berths have scores
    for bc in eligible_berths:
        suitability_scores.setdefault(bc, 0.01)

    # Rank WITH uncertainty (Phase 3)
    options = dr.rank(
        suitability_scores, wait_predictions, service_predictions,
        berth_info_map, top_k,
        service_uncertainty=service_uncertainty,
        delay_uncertainty=delay_uncertainty,
    )

    # ── Decouple Confidence: Use ConfidenceCalculator for proper multi-factor scoring ──
    from engines.core.decision.confidence import ConfidenceCalculator
    conf_calc = ConfidenceCalculator()

    for opt in options:
        bi = berth_info_map.get(opt.berth_code, {})
        compat_score = bi.get("_compat_score", 50.0)
        data_quality_gate = bi.get("_data_quality", "")
        # Normalize data quality gate string
        if "GREEN" in str(data_quality_gate).upper():
            dq_gate = "GREEN"
        elif "YELLOW" in str(data_quality_gate).upper():
            dq_gate = "YELLOW"
        else:
            dq_gate = "RED"

        # Get feasibility check results (if available from constraint library)
        feas_checks = None
        feas_result = bi.get("_feas_result")
        if feas_result:
            feas_checks = feas_result.constraint_results

        # Service uncertainty ratio
        svc_uncert_ratio = 0.0
        if service_uncertainty and opt.berth_code in service_uncertainty:
            svc_uncert_ratio = service_uncertainty[opt.berth_code].uncertainty_ratio

        conf_result = conf_calc.compute(
            feasibility_checks=feas_checks,
            compatibility_score=compat_score,
            data_quality_gate=dq_gate,
            service_uncertainty_ratio=svc_uncert_ratio,
        )
        opt.confidence = conf_result.confidence_pct
        opt.risk_score = {"Low": 20, "Medium": 50, "High": 80}.get(conf_result.risk_level, 50)

    # Generate structured explanations + backward-compatible pros/cons
    try:
        from engines.analytics.explanation.structured_explanation import (
            StructuredExplanationEngine, build_comparison_insight,
        )
        _struct_engine = StructuredExplanationEngine()

        structured_results = []
        for opt in options:
            bi = berth_info_map.get(opt.berth_code, {})
            # Uncertainty bounds
            svc_lo = svc_hi = opt.expected_service_hours
            dly_lo = dly_hi = opt.expected_wait_hours
            if service_uncertainty and opt.berth_code in service_uncertainty:
                svc_lo = service_uncertainty[opt.berth_code].lower
                svc_hi = service_uncertainty[opt.berth_code].upper
            if delay_uncertainty and opt.berth_code in delay_uncertainty:
                dly_lo = delay_uncertainty[opt.berth_code].lower
                dly_hi = delay_uncertainty[opt.berth_code].upper

            struct_expl = _struct_engine.explain(
                vessel=vessel,
                berth_info=bi,
                wait_hours=opt.expected_wait_hours,
                service_hours=opt.expected_service_hours,
                wait_lower=dly_lo,
                wait_upper=dly_hi,
                service_lower=svc_lo,
                service_upper=svc_hi,
            )
            opt.structured_explanation = struct_expl
            opt.compact_reason = struct_expl.compact_summary
            # Derive pros/cons from structured data
            opt.pros = struct_expl.get_pros()[:6]
            opt.cons = struct_expl.get_cons()[:6]
            opt.explanation = struct_expl.final_summary
            structured_results.append(struct_expl)

        # Bonus: comparison insights for rank 2+ vs rank 1
        if len(structured_results) >= 2:
            for i, opt in enumerate(options[1:], 1):
                try:
                    cmp = build_comparison_insight(
                        structured_results[i], structured_results[0],
                        options[i].expected_wait_hours, options[0].expected_wait_hours,
                        options[i].expected_service_hours, options[0].expected_service_hours,
                    )
                    if cmp:
                        opt.structured_explanation.trade_off_sentence = cmp
                except Exception:
                    pass

    except Exception:
        # Fallback to legacy pros/cons if structured engine fails
        for opt in options:
            _generate_pros_cons(
                opt, vessel, berth_info_map,
                wait_predictions, service_predictions,
                service_uncertainty, delay_uncertainty,
            )

    return options


def _generate_pros_cons(
    option: BerthOption,
    vessel: dict,
    berth_info_map: dict,
    wait_preds: dict,
    svc_preds: dict,
    svc_uncertainty: Dict[str, QuantilePrediction] = None,
    dly_uncertainty: Dict[str, QuantilePrediction] = None,
):
    """Generate human-readable pros and cons with uncertainty & provenance."""
    bi = berth_info_map.get(option.berth_code, {})
    vessel_loa = float(vessel.get("loa", 0))
    vessel_beam = float(vessel.get("beam", 0))
    vessel_draft = float(vessel.get("draft", vessel.get("adraft", 0)))

    pros = []
    cons = []

    # Data quality indicator
    dq = bi.get("_data_quality", bi.get("data_quality", ""))
    if dq == "green":
        pros.append("✅ Spec-verified berth data")
    elif dq == "yellow":
        pros.append("⚠️ Partially spec-backed data")
    elif dq == "red":
        cons.append("🔴 Low data quality — verify constraints manually")

    # Suitability
    if option.suitability_score > 50:
        pros.append(f"High suitability ({option.suitability_score:.0f}%)")
    elif option.suitability_score > 20:
        pros.append(f"Moderate suitability ({option.suitability_score:.0f}%)")
    else:
        cons.append(f"Low historical usage ({option.suitability_score:.0f}%)")

    # Wait time with uncertainty
    if dly_uncertainty and option.berth_code in dly_uncertainty:
        dq = dly_uncertainty[option.berth_code]
        if dq.point <= 2:
            pros.append(f"Short wait ({dq.point:.1f}h, range {dq.lower:.1f}-{dq.upper:.1f}h)")
        elif dq.point <= 6:
            pros.append(f"Acceptable wait ({dq.point:.1f}h ±{dq.confidence_width/2:.1f}h)")
        else:
            cons.append(f"Long wait ({dq.point:.1f}h, could be {dq.upper:.1f}h)")
    else:
        if option.expected_wait_hours <= 2:
            pros.append(f"Short expected wait ({option.expected_wait_hours:.1f}h)")
        elif option.expected_wait_hours <= 6:
            pros.append(f"Acceptable wait time ({option.expected_wait_hours:.1f}h)")
        else:
            cons.append(f"Long expected wait ({option.expected_wait_hours:.1f}h)")

    # LOA fit with provenance
    max_loa = bi.get("max_loa_m", 300)
    loa_source = bi.get("loa_source", "")
    if vessel_loa > 0 and max_loa > 0:
        ratio = vessel_loa / max_loa
        source_tag = f" [{loa_source}]" if loa_source else ""
        if ratio < 0.7:
            pros.append(f"Comfortable LOA fit{source_tag}")
        elif ratio < 0.9:
            pros.append(f"Good LOA fit{source_tag}")
        else:
            cons.append(f"Tight LOA fit — limited margin{source_tag}")

    # Beam fit
    max_beam = bi.get("max_beam_m", 999)
    if vessel_beam > 0 and max_beam < 999:
        beam_ratio = vessel_beam / max_beam
        if beam_ratio < 0.7:
            pros.append("Comfortable beam fit")
        elif beam_ratio < 0.9:
            pros.append("Good beam fit")
        else:
            cons.append("Tight beam fit — limited margin")

    # Depth
    depth = bi.get("depth_m", 15)
    if vessel_draft > 0 and depth > 0:
        clearance = depth - vessel_draft
        if clearance > 3:
            pros.append(f"Good UKC ({clearance:.1f}m)")
        elif clearance > 1:
            pros.append(f"Adequate clearance ({clearance:.1f}m)")
        else:
            cons.append(f"Tight clearance ({clearance:.1f}m) — tide sensitive")

    # Service time with uncertainty
    if svc_uncertainty and option.berth_code in svc_uncertainty:
        sq = svc_uncertainty[option.berth_code]
        if sq.point < 12:
            pros.append(f"Quick turnaround ({sq.point:.0f}h, best case {sq.lower:.0f}h)")
        elif sq.point > 48:
            cons.append(f"Long service ({sq.point:.0f}h, up to {sq.upper:.0f}h)")
        # Flag high uncertainty
        if sq.uncertainty_ratio > 0.6:
            cons.append(f"⚠️ High prediction uncertainty (±{sq.confidence_width/2:.0f}h)")
    else:
        if option.expected_service_hours < 12:
            pros.append(f"Quick turnaround ({option.expected_service_hours:.0f}h)")
        elif option.expected_service_hours > 48:
            cons.append(f"Long service time ({option.expected_service_hours:.0f}h)")

    # Terminal type and cargo
    terminal_type = bi.get("terminal_type", "")
    if terminal_type:
        pros.append(f"Terminal: {terminal_type}")

    cargo_cats = bi.get("cargo_categories", [])
    if cargo_cats:
        pros.append(f"Handles: {', '.join(list(cargo_cats)[:3])} cargo")

    # Tidal restriction
    if bi.get("tidal_restricted"):
        cons.append("Tidal restricted — timing constraints apply")

    # Equipment
    if bi.get("equipment"):
        pros.append(f"Equipment: {', '.join(bi['equipment'][:3])}")

    option.pros = pros
    option.cons = cons

    # Explanation narrative with uncertainty
    parts = []
    if pros:
        parts.append(f"Recommended for: {'; '.join(pros[:2])}.")
    if cons:
        parts.append(f"Considerations: {'; '.join(cons[:2])}.")

    # Add uncertainty to explanation
    if svc_uncertainty and option.berth_code in svc_uncertainty:
        sq = svc_uncertainty[option.berth_code]
        parts.append(
            f"Service: {sq.point:.0f}h ({sq.lower:.0f}-{sq.upper:.0f}h)."
        )

    parts.append(f"Confidence: {option.confidence:.0f}%. Wait: {option.expected_wait_hours:.1f}h.")
    option.explanation = " ".join(parts)
