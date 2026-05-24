"""
Agentic AI Explainer — Decision Explanations, Trade-offs, and What-If Analysis.

Provides:
  - Structured explanations for berth assignments
  - Trade-off analysis between top-k options
  - What-if simulations (toggle levers, change constraints)
  - Sensitivity analysis per lever
  - Override suggestions with impact estimates
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from optimization_engine.constraint_model import (
    VesselInput, BerthInput, SchedulerConfig, SolverResult,
    AssignmentResult, OPTIMAL, FEASIBLE,
)
from optimization_engine.scheduler import RollingHorizonScheduler
from cost_engine.cost_model import CostEngine, CostConfig


@dataclass
class TradeOffItem:
    """Comparison of one metric across options."""
    metric: str
    unit: str = ""
    values: Dict[str, float] = field(default_factory=dict)  # berth_code → value
    best_option: str = ""
    explanation: str = ""


@dataclass
class TradeOffReport:
    """Full trade-off analysis between top options."""
    items: List[TradeOffItem] = field(default_factory=list)
    summary: str = ""


@dataclass
class WhatIfResult:
    """Result of a what-if simulation."""
    scenario_name: str
    change_description: str
    baseline_kpis: Dict[str, float] = field(default_factory=dict)
    scenario_kpis: Dict[str, float] = field(default_factory=dict)
    delta: Dict[str, float] = field(default_factory=dict)        # metric → change
    impact_summary: str = ""


@dataclass
class SensitivityResult:
    """Sensitivity of a metric to a lever change."""
    lever_name: str
    metric_name: str
    baseline_value: float = 0.0
    values: List[Tuple[float, float]] = field(default_factory=list)  # (lever_val, metric_val)
    sensitivity: float = 0.0    # slope
    interpretation: str = ""


@dataclass
class AssignmentExplanation:
    """Structured explanation for a single vessel -> berth assignment."""
    vessel_id: str
    berth_code: str
    headline: str = ""
    reasons: List[str] = field(default_factory=list)
    alternatives_considered: int = 0
    trade_offs: List[str] = field(default_factory=list)
    confidence_note: str = ""
    cost_note: str = ""
    risk_note: str = ""
    # Phase 3: Uncertainty and provenance
    service_time_range: str = ""   # e.g., "24h (20-28h)"
    delay_range: str = ""          # e.g., "2.0h (1.0-3.5h)"
    data_provenance: str = ""      # e.g., "Spec-backed" or "History-derived"
    constraint_sources: List[str] = field(default_factory=list)


class AgenticExplainer:
    """
    Generates structured, natural language explanations for scheduling decisions.

    Usage:
        explainer = AgenticExplainer()
        explanation = explainer.explain_assignment(assignment, result, vessels, berths)
        trade_off = explainer.trade_off_analysis(result, vessels, berths)
        what_if = explainer.what_if(vessels, berths, config, change_desc, modified_config)
    """

    def __init__(self, cost_config: Optional[CostConfig] = None):
        self.cost_engine = CostEngine(cost_config)

    def explain_assignment(
        self,
        assignment: AssignmentResult,
        full_result: SolverResult,
        vessels: Dict[str, VesselInput],
        berths: Dict[str, BerthInput],
    ) -> AssignmentExplanation:
        """Generate structured explanation for why a berth was selected."""
        v = vessels.get(assignment.vessel_id)
        b = berths.get(assignment.berth_code)

        if not v or not b:
            return AssignmentExplanation(
                vessel_id=assignment.vessel_id,
                berth_code=assignment.berth_code,
                headline="Unable to generate explanation — missing data.",
            )

        reasons = []
        trade_offs = []

        # Physical fit
        if v.loa_m > 0 and b.max_loa_m > 0:
            loa_margin = b.max_loa_m - v.loa_m
            loa_pct = loa_margin / b.max_loa_m * 100
            reasons.append(
                f"LOA {v.loa_m:.0f}m fits berth {b.berth_code} "
                f"(max {b.max_loa_m:.0f}m, margin {loa_margin:.0f}m / {loa_pct:.0f}%)"
            )

        if v.draft_m > 0:
            ukc = b.depth_m - v.draft_m
            reasons.append(
                f"Draft {v.draft_m:.1f}m, depth {b.depth_m:.1f}m "
                f"(UKC: {ukc:.1f}m)"
            )

        # Waiting time
        wait_h = assignment.waiting_minutes / 60
        if wait_h <= 2:
            reasons.append(f"Minimal wait: {wait_h:.1f} hours")
        elif wait_h <= 6:
            reasons.append(f"Acceptable wait: {wait_h:.1f} hours")
        else:
            trade_offs.append(
                f"High wait time: {wait_h:.1f} hours. "
                f"Consider redistribution if congestion permits."
            )

        # SLA
        if assignment.sla_exceeded:
            excess_h = assignment.sla_excess_minutes / 60
            trade_offs.append(
                f"SLA violation: wait exceeds limit by {excess_h:.1f} hours."
            )

        # Preferred berth
        if assignment.is_preferred_berth:
            reasons.append("Assigned to contractually preferred berth.")

        # Cost analysis
        cost_bd = self.cost_engine.compute_vessel_cost(
            wait_hours=wait_h,
            service_hours=assignment.service_minutes / 60,
            cargo_tons=v.cargo_tons,
            demurrage_rate=v.demurrage_cost_per_hr,
            sla_max_wait_hours=v.sla_max_wait_minutes / 60,
        )
        cost_note = (
            f"Est. cost: ${cost_bd.total_cost:,.0f} "
            f"(wait: ${cost_bd.waiting_cost:,.0f}, "
            f"revenue: ${cost_bd.revenue:,.0f})"
        )

        # Headline
        headline = (
            f"Vessel {v.name or v.vessel_id} -> Berth {b.berth_name or b.berth_code}: "
            f"wait {wait_h:.1f}h, service {assignment.service_minutes/60:.0f}h"
        )

        return AssignmentExplanation(
            vessel_id=assignment.vessel_id,
            berth_code=assignment.berth_code,
            headline=headline,
            reasons=reasons,
            alternatives_considered=len(berths) - 1,
            trade_offs=trade_offs,
            cost_note=cost_note,
        )

    def explain_recommendation(
        self,
        berth_option,  # BerthOption from ml_models
        vessel: dict,
        berth_info: dict,
    ) -> AssignmentExplanation:
        """
        Generate rich explanation for a recommender BerthOption.
        Includes uncertainty ranges, data provenance, and constraint sources.
        """
        reasons = []
        trade_offs = []
        constraint_sources = []

        # Data provenance
        dq = berth_info.get("_data_quality", "")
        if dq == "green":
            data_prov = "Spec-verified"
            reasons.append("✅ Berth data verified from official specifications")
        elif dq == "yellow":
            data_prov = "Partially spec-backed"
        else:
            data_prov = "History-derived"
            if dq == "red":
                trade_offs.append("🟡 Low data quality — verify constraints manually")

        # LOA fit with source
        vessel_loa = float(vessel.get("loa", 0))
        max_loa = berth_info.get("max_loa_m", 300)
        loa_src = berth_info.get("loa_source", "history")
        if vessel_loa > 0 and max_loa > 0:
            margin = max_loa - vessel_loa
            reasons.append(
                f"LOA {vessel_loa:.0f}m fits (max {max_loa:.0f}m, margin {margin:.0f}m) [{loa_src}]"
            )
            constraint_sources.append(f"LOA limit: {loa_src}")

        # Draft with UKC
        vessel_draft = float(vessel.get("draft", vessel.get("adraft", 0)))
        depth = berth_info.get("depth_m", 15)
        if vessel_draft > 0 and depth > 0:
            ukc = depth - vessel_draft
            reasons.append(f"Draft {vessel_draft:.1f}m, depth {depth:.1f}m (UKC: {ukc:.1f}m)")

        # Service time with uncertainty
        svc_range = ""
        if berth_option.service_time_lower > 0 and berth_option.service_time_upper > 0:
            svc_range = (
                f"{berth_option.expected_service_hours:.0f}h "
                f"({berth_option.service_time_lower:.0f}-{berth_option.service_time_upper:.0f}h)"
            )
            reasons.append(f"Service time: {svc_range}")
        elif berth_option.expected_service_hours > 0:
            svc_range = f"{berth_option.expected_service_hours:.0f}h"
            reasons.append(f"Est. service time: {svc_range}")

        # Delay with uncertainty
        dly_range = ""
        if berth_option.delay_lower > 0 or berth_option.delay_upper > 0:
            dly_range = (
                f"{berth_option.expected_wait_hours:.1f}h "
                f"({berth_option.delay_lower:.1f}-{berth_option.delay_upper:.1f}h)"
            )
        else:
            dly_range = f"{berth_option.expected_wait_hours:.1f}h"

        # Suitability
        if berth_option.suitability_score > 50:
            reasons.append(f"High suitability ({berth_option.suitability_score:.0f}%)")
        elif berth_option.suitability_score > 20:
            reasons.append(f"Moderate suitability ({berth_option.suitability_score:.0f}%)")
        else:
            trade_offs.append(f"Low suitability ({berth_option.suitability_score:.0f}%)")

        # Equipment
        equip = berth_info.get("equipment", [])
        if equip:
            reasons.append(f"Equipment: {', '.join(equip[:3])}")

        # Confidence explanation
        conf_note = (
            f"Confidence: {berth_option.confidence:.0f}% "
            f"(data: {data_prov})"
        )

        headline = (
            f"Berth {berth_option.berth_name} scores {berth_option.confidence:.0f}% — "
            f"wait {berth_option.expected_wait_hours:.1f}h, service {berth_option.expected_service_hours:.0f}h"
        )

        return AssignmentExplanation(
            vessel_id=vessel.get("name", "vessel"),
            berth_code=berth_option.berth_code,
            headline=headline,
            reasons=reasons,
            trade_offs=trade_offs,
            confidence_note=conf_note,
            service_time_range=svc_range,
            delay_range=dly_range,
            data_provenance=data_prov,
            constraint_sources=constraint_sources,
        )

    def trade_off_analysis(
        self,
        result: SolverResult,
        vessels: Dict[str, VesselInput],
        berths: Dict[str, BerthInput],
    ) -> TradeOffReport:
        """Compare all assignments across key metrics."""
        items = []

        if not result.assignments:
            return TradeOffReport(summary="No assignments to analyze.")

        # Waiting time comparison
        wait_vals = {}
        for a in result.assignments:
            wait_vals[a.berth_code] = a.waiting_minutes / 60

        best_wait = min(wait_vals, key=wait_vals.get) if wait_vals else ""
        items.append(TradeOffItem(
            metric="Waiting Time",
            unit="hours",
            values=wait_vals,
            best_option=best_wait,
            explanation=f"Berth {best_wait} offers shortest wait at {wait_vals.get(best_wait, 0):.1f}h",
        ))

        # Service time comparison
        svc_vals = {a.berth_code: a.service_minutes / 60 for a in result.assignments}
        items.append(TradeOffItem(
            metric="Service Time", unit="hours", values=svc_vals,
        ))

        # Cost comparison
        for a in result.assignments:
            v = vessels.get(a.vessel_id)
            if v:
                cost = self.cost_engine.compute_vessel_cost(
                    wait_hours=a.waiting_minutes / 60,
                    service_hours=a.service_minutes / 60,
                    cargo_tons=v.cargo_tons,
                    demurrage_rate=v.demurrage_cost_per_hr,
                    sla_max_wait_hours=v.sla_max_wait_minutes / 60,
                )

        summary = f"Analyzed {len(result.assignments)} assignments across {len(items)} metrics."

        return TradeOffReport(items=items, summary=summary)

    def what_if(
        self,
        vessels: List[VesselInput],
        berths: List[BerthInput],
        baseline_config: SchedulerConfig,
        scenario_name: str,
        change_description: str,
        modified_config: SchedulerConfig,
    ) -> WhatIfResult:
        """
        Run a what-if scenario: compare baseline vs modified configuration.

        Example:
            "If FCFS is disabled, vessel A moves to berth 3
             reducing waiting by 4.2h but increasing idle cost by 2%"
        """
        # Run baseline
        scheduler = RollingHorizonScheduler(baseline_config)
        baseline = scheduler.optimize(vessels, berths)
        baseline_kpis = baseline.solver_result.kpis if baseline.solver_result else {}

        # Run scenario
        scheduler2 = RollingHorizonScheduler(modified_config)
        scenario = scheduler2.optimize(vessels, berths)
        scenario_kpis = scenario.solver_result.kpis if scenario.solver_result else {}

        # Compute deltas
        delta = {}
        all_keys = set(list(baseline_kpis.keys()) + list(scenario_kpis.keys()))
        for k in all_keys:
            bv = baseline_kpis.get(k, 0)
            sv = scenario_kpis.get(k, 0)
            if isinstance(bv, (int, float)) and isinstance(sv, (int, float)):
                delta[k] = round(sv - bv, 2)

        # Generate impact summary
        impact_parts = []
        wait_delta = delta.get("avg_waiting_hours", 0)
        if abs(wait_delta) > 0.1:
            direction = "reducing" if wait_delta < 0 else "increasing"
            impact_parts.append(
                f"{direction} average waiting time by {abs(wait_delta):.1f} hours"
            )

        util_delta = delta.get("berth_utilization_pct", 0)
        if abs(util_delta) > 0.5:
            direction = "improving" if util_delta > 0 else "reducing"
            impact_parts.append(
                f"{direction} berth utilization by {abs(util_delta):.1f}%"
            )

        sla_delta = delta.get("sla_violations", 0)
        if sla_delta != 0:
            direction = "increasing" if sla_delta > 0 else "decreasing"
            impact_parts.append(
                f"{direction} SLA violations by {abs(int(sla_delta))}"
            )

        impact_summary = (
            f"{change_description}: {', '.join(impact_parts)}."
            if impact_parts else
            f"{change_description}: no significant impact detected."
        )

        return WhatIfResult(
            scenario_name=scenario_name,
            change_description=change_description,
            baseline_kpis=baseline_kpis,
            scenario_kpis=scenario_kpis,
            delta=delta,
            impact_summary=impact_summary,
        )

    def sensitivity_analysis(
        self,
        vessels: List[VesselInput],
        berths: List[BerthInput],
        base_config: SchedulerConfig,
        lever_name: str,
        lever_values: List[float],
        metric_name: str = "avg_waiting_hours",
    ) -> SensitivityResult:
        """
        Measure sensitivity of a metric to a lever by sweeping values.

        Example:
            result = explainer.sensitivity_analysis(
                vessels, berths, config,
                lever_name="w_waiting",
                lever_values=[0.0, 0.25, 0.5, 0.75, 1.0],
                metric_name="avg_waiting_hours",
            )
        """
        values = []

        for lval in lever_values:
            # Create modified config
            cfg = SchedulerConfig(**{
                k: getattr(base_config, k)
                for k in base_config.__dataclass_fields__
            })
            if hasattr(cfg, lever_name):
                setattr(cfg, lever_name, lval)

            scheduler = RollingHorizonScheduler(cfg)
            snapshot = scheduler.optimize(vessels, berths)

            if snapshot.solver_result and snapshot.solver_result.kpis:
                metric_val = snapshot.solver_result.kpis.get(metric_name, 0)
            else:
                metric_val = 0

            values.append((lval, metric_val))

        # Compute sensitivity (simple slope)
        if len(values) >= 2:
            x_vals = [v[0] for v in values]
            y_vals = [v[1] for v in values]
            x_range = max(x_vals) - min(x_vals)
            y_range = max(y_vals) - min(y_vals) if y_vals else 0
            sensitivity = y_range / x_range if x_range > 0 else 0
        else:
            sensitivity = 0

        baseline_val = values[0][1] if values else 0

        interpretation = (
            f"Varying {lever_name} from {lever_values[0]} to {lever_values[-1]} "
            f"changes {metric_name} by {abs(values[-1][1] - values[0][1]):.2f} "
            f"(sensitivity: {sensitivity:.3f})"
        ) if values else "Insufficient data for sensitivity analysis."

        return SensitivityResult(
            lever_name=lever_name,
            metric_name=metric_name,
            baseline_value=baseline_val,
            values=values,
            sensitivity=sensitivity,
            interpretation=interpretation,
        )
