"""
Spec Ingestion — Reads Berth Spec Sheets & Operational Capability
==================================================================
Transforms raw Excel data from:
  - Berth_configurations.xlsx → Physical specs (LOA, draft, depth, beam, DWT, UKC)
  - Operational_Capability_of_Berth.xlsx → Cargo/operation capability
  - Historical port call logs → Fallback data + vessel type inference

Into canonical BerthSpec objects with full data provenance tracking.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.db.models.data_models import (
    BerthSpec, DataSource, PortMaster, ProvenanceField, QualityGate,
)
from backend.db.repositories.quality import score_berth_quality, QualityReport, score_history_quality
from backend.config.settings import settings

logger = logging.getLogger(__name__)
_INFERRED_BERTH_LIMIT_WARNING = (
    "Berth spec limit missing; using conservative inferred limit from historical dimensions."
)


def _safe_float(val, default: float = 0.0) -> float:
    """Safely convert value to float, handling 'No Restrictions' etc."""
    if val is None or pd.isna(val):
        return default
    s = str(val).strip()
    if s.lower() in ("no restrictions", "", "nan", "none"):
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _safe_bool(val, true_values=("yes", "true", "1", "available")) -> bool:
    if val is None or pd.isna(val):
        return False
    return str(val).strip().lower() in true_values


def _is_no_restriction(val) -> bool:
    if val is None or pd.isna(val):
        return False
    return str(val).strip().lower() == "no restrictions"


# ── Berth Configuration Ingestion ────────────────────────────────────────────

def ingest_berth_configurations(excel_path: str | Path) -> Dict[str, BerthSpec]:
    """
    Read Berth_configurations.xlsx and build BerthSpec objects.
    
    The Excel has a property-value format:
      Each row = one property for one berth.
      Columns: berthCode, berthName, terminalCode, terminalName, portCode, portName,
               propertyName, propertyValue, propertyUOM, BerthType, Berthingside
    
    Returns:
        Dict[berth_code, BerthSpec] with physical constraints from spec.
    """
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()
    logger.info(f"Read {len(df)} property rows from {Path(excel_path).name}")

    berths: Dict[str, BerthSpec] = {}

    # Group by berth
    for (bc, bn, tc, tn, pc, pn), group in df.groupby(
        ["berthCode", "berthName", "terminalCode", "terminalName", "portCode", "portName"],
        dropna=False,
    ):
        bc_str = str(int(bc)) if pd.notna(bc) else str(bc)

        # Get BerthType and Berthingside from first row
        berth_type = str(group["BerthType"].iloc[0]) if "BerthType" in group.columns else "Berth"
        berthing_side = str(group["Berthingside"].iloc[0]) if "Berthingside" in group.columns else "Either"

        spec = BerthSpec(
            berth_code=bc_str,
            berth_name=str(bn) if pd.notna(bn) else "",
            terminal_code=str(int(tc)) if pd.notna(tc) else "",
            terminal_name=str(tn) if pd.notna(tn) else "",
            port_code=str(int(pc)) if pd.notna(pc) else "",
            port_name=str(pn) if pd.notna(pn) else "",
            berth_type=berth_type if pd.notna(berth_type) else "Berth",
            berthing_side=berthing_side if pd.notna(berthing_side) else "Either",
        )

        # Parse each property
        props = {}
        for _, row in group.iterrows():
            pname = str(row.get("propertyName", "")).strip()
            pval = row.get("propertyValue")
            props[pname] = pval

        # Map properties to BerthSpec fields
        # Physical constraints — all from SPEC source
        loa_val = _safe_float(props.get("Max Length Overall (LOA)"))
        if loa_val > 0:
            spec.max_loa_m = ProvenanceField.from_spec(loa_val, "From Berth_configurations.xlsx")
        elif _is_no_restriction(props.get("Max Length Overall (LOA)")):
            spec.max_loa_m = ProvenanceField.from_spec(999.0, "No restriction per spec")
            spec.max_loa_m.quality = QualityGate.YELLOW

        min_loa_val = _safe_float(props.get("Min Length Overall (LOA)"))
        if min_loa_val > 0:
            spec.min_loa_m = ProvenanceField.from_spec(min_loa_val)

        draft_val = _safe_float(props.get("Max Draft"))
        if draft_val > 0:
            spec.max_draft_m = ProvenanceField.from_spec(draft_val, "From Berth_configurations.xlsx")
        elif _is_no_restriction(props.get("Max Draft")):
            spec.max_draft_m = ProvenanceField.from_spec(30.0, "No restriction per spec")
            spec.max_draft_m.quality = QualityGate.YELLOW

        depth_val = _safe_float(props.get("Max Depth"))
        if depth_val > 0:
            spec.max_depth_m = ProvenanceField.from_spec(depth_val, "From Berth_configurations.xlsx")
        elif _is_no_restriction(props.get("Max Depth")):
            spec.max_depth_m = ProvenanceField.from_spec(30.0, "No restriction per spec")
            spec.max_depth_m.quality = QualityGate.YELLOW

        beam_val = _safe_float(props.get("Max Beam (Width)"))
        if beam_val > 0:
            spec.max_beam_m = ProvenanceField.from_spec(beam_val, "From Berth_configurations.xlsx")
        elif _is_no_restriction(props.get("Max Beam (Width)")):
            spec.max_beam_m = ProvenanceField.from_spec(999.0, "No restriction per spec")
            spec.max_beam_m.quality = QualityGate.YELLOW

        dwt_val = _safe_float(props.get("Max Deadweight (DWT)"))
        if dwt_val > 0:
            spec.max_dwt = ProvenanceField.from_spec(dwt_val)
        elif _is_no_restriction(props.get("Max Deadweight (DWT)")):
            spec.max_dwt = ProvenanceField.from_spec(0, "No DWT restriction per spec")
            spec.max_dwt.quality = QualityGate.YELLOW

        disp_val = _safe_float(props.get("Max Displacement"))
        if disp_val > 0:
            spec.max_displacement = ProvenanceField.from_spec(disp_val)
        elif _is_no_restriction(props.get("Max Displacement")):
            spec.max_displacement = ProvenanceField.from_spec(0, "No displacement restriction")
            spec.max_displacement.quality = QualityGate.YELLOW

        # UKC
        ukc_val = _safe_float(props.get("UKC (Underkeel Clearance)"))
        if ukc_val > 0:
            spec.ukc_m = ProvenanceField.from_spec(ukc_val, "From spec sheet")

        # Channel constraints
        ch_depth = _safe_float(props.get("Channel Max Depth"))
        if ch_depth > 0:
            spec.channel_max_depth_m = ProvenanceField.from_spec(ch_depth)

        ch_draft = _safe_float(props.get("Channel Max Draft"))
        if ch_draft > 0:
            spec.channel_max_draft_m = ProvenanceField.from_spec(ch_draft)

        ch_ukc = _safe_float(props.get("Channel UKC (Underkeel Clearance)"))
        if ch_ukc > 0:
            spec.channel_ukc_m = ProvenanceField.from_spec(ch_ukc)

        # Air draft
        air_draft = _safe_float(props.get("Max Air Draft (WLTHC)"))
        if air_draft > 0:
            spec.max_air_draft_m = ProvenanceField.from_spec(air_draft)

        # Operational booleans
        spec.tidal_restricted = _safe_bool(props.get("Tidal Restricted"))
        spec.shore_gangway = _safe_bool(props.get("Shore Gangway"))
        spec.bunkering_allowed = _safe_bool(props.get("Bunkering"))
        spec.bunkering_during_ops = _safe_bool(props.get("Bunkering During Ops"))
        spec.bunkering_after_ops = _safe_bool(props.get("Bunkering After Ops"))

        # Seabed & water density
        spec.seabed_type = str(props.get("Seabed", "")) if props.get("Seabed") else ""
        spec.water_density = str(props.get("Water Density (g/cm3)", "")) if props.get("Water Density (g/cm3)") else ""

        berths[bc_str] = spec

    logger.info(f"Built {len(berths)} BerthSpec objects from spec sheet")
    return berths


# ── Operational Capability Ingestion ─────────────────────────────────────────

def ingest_operational_capability(
    excel_path: str | Path,
    berths: Dict[str, BerthSpec],
) -> Dict[str, BerthSpec]:
    """
    Read Operational_Capability_of_Berth.xlsx and enrich BerthSpec objects.
    
    Adds: supported operations, commodity lists, cargo categories.
    
    Columns: berthCode, berthName, terminalName, terminalCode, terminalType,
             operation, commodity, commodityGroup, cargoCategory
    """
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()
    logger.info(f"Read {len(df)} capability rows from {Path(excel_path).name}")

    for bc, group in df.groupby("berthCode", dropna=False):
        bc_str = str(int(bc)) if pd.notna(bc) else str(bc)

        spec = berths.get(bc_str)
        if not spec:
            # Create a new spec for berths only in operational data
            first_row = group.iloc[0]
            spec = BerthSpec(
                berth_code=bc_str,
                berth_name=str(first_row.get("berthName", "")),
                terminal_code=str(int(first_row.get("terminalCode", 0))) if pd.notna(first_row.get("terminalCode")) else "",
                terminal_name=str(first_row.get("terminalName", "")),
                port_code=str(int(first_row.get("portCode", 0))) if pd.notna(first_row.get("portCode")) else "",
                port_name=str(first_row.get("port", "")),
            )
            berths[bc_str] = spec

        # Set terminal type from operational data
        tt = group["terminalType"].dropna().unique()
        if len(tt) > 0:
            spec.terminal_type = str(tt[0])

        # Collect operations, commodities, cargo categories
        operations = set()
        commodities = set()
        commodity_groups = set()
        cargo_cats = set()

        for _, row in group.iterrows():
            op = str(row.get("operation", "")).strip()
            if op:
                operations.add(op)
            comm = str(row.get("commodity", "")).strip()
            if comm and comm.lower() != "nan":
                commodities.add(comm)
            cg = str(row.get("commodityGroup", "")).strip()
            if cg and cg.lower() != "nan":
                commodity_groups.add(cg)
            cc = str(row.get("cargoCategory", "")).strip()
            if cc and cc.lower() != "nan":
                cargo_cats.add(cc)

        spec.supported_operations = sorted(operations)
        spec.supported_commodities = sorted(commodities)
        spec.commodity_groups = sorted(commodity_groups)
        spec.cargo_categories = cargo_cats

    logger.info(f"Enriched {len(berths)} berths with operational capability")
    return berths


# ── Historical Enrichment ────────────────────────────────────────────────────

def enrich_from_history(
    berths: Dict[str, BerthSpec],
    df_history: pd.DataFrame,
) -> Dict[str, BerthSpec]:
    """
    Enrich BerthSpec objects with data derived from historical port calls.
    
    This is FALLBACK data — used only when spec/operational data is missing.
    All values marked with DataSource.HISTORICAL.
    
    Derives:
      - allowed_vessel_types (if not from operational data)
      - max LOA/draft seen (for comparison, not as limits)
      - avg service times
      - equipment types (always assumed for now)
    """
    df = df_history.copy()

    # Normalize column names
    col_map = {}
    for c in df.columns:
        col_map[c.lower().strip()] = c

    bc_col = col_map.get("berthcode", col_map.get("berth_code", None))
    vt_col = col_map.get("vesseltype", col_map.get("vessel_type", None))
    loa_col = col_map.get("loa", None)
    draft_col = col_map.get("adraft", col_map.get("adraught", col_map.get("draft", None)))
    svc_col = col_map.get("berth_occupancy_h", None)

    if not bc_col:
        logger.warning("No berth code column found in history — skipping enrichment")
        return berths

    for bc_val, group in df.groupby(bc_col, dropna=False):
        bc_str = str(int(bc_val)) if pd.notna(bc_val) else str(bc_val)
        spec = berths.get(bc_str)

        if not spec:
            continue  # Only enrich berths we already know about

        # Vessel types from history (fallback if no operational data)
        if vt_col and not spec.allowed_vessel_types:
            hist_types = sorted(set(
                str(v).strip() for v in group[vt_col].dropna().unique()
                if str(v).strip() and str(v).strip().lower() != "nan"
            ))
            if hist_types:
                spec.allowed_vessel_types = hist_types
                spec.vessel_type_source = DataSource.HISTORICAL

        # If already have vessel types from operational, keep but supplement
        elif vt_col and spec.vessel_type_source != DataSource.HISTORICAL:
            # Don't override spec/operational data
            pass

        # Max LOA/draft seen in history (informational, not as limits)
        if loa_col:
            loa_vals = pd.to_numeric(group[loa_col], errors="coerce").dropna()
            if len(loa_vals) > 0:
                spec.historical_max_loa_seen = float(loa_vals.max())

        if draft_col:
            draft_vals = pd.to_numeric(group[draft_col], errors="coerce").dropna()
            if len(draft_vals) > 0:
                spec.historical_max_draft_seen = float(draft_vals.max())

        # Average service time
        if svc_col:
            svc_vals = pd.to_numeric(group[svc_col], errors="coerce").dropna()
            svc_vals = svc_vals[(svc_vals > 0) & (svc_vals < 1000)]
            if len(svc_vals) > 0:
                spec.historical_avg_service_hours = float(svc_vals.mean())

        # Historical vessel count
        spec.historical_vessel_count = len(group)

        # Fallback for LOA/draft limits if spec doesn't have them
        if spec.get_max_loa() <= 0 and spec.historical_max_loa_seen > 0:
            # FIX (Phase 5): Use a conservative factor, not a behavior-cloning buffer above history.
            logger.warning("%s berth_code=%s field=max_loa_m", _INFERRED_BERTH_LIMIT_WARNING, bc_str)
            factor = settings.berth_limit_inference_factor
            spec.max_loa_m = ProvenanceField.from_history(
                spec.historical_max_loa_seen * factor,
                f"Derived conservatively from history max {spec.historical_max_loa_seen:.0f}m * {factor:.2f}"
            )

        if spec.get_max_draft() <= 0 and spec.historical_max_draft_seen > 0:
            # FIX (Phase 5): Draft fallback also uses the same conservative inference policy.
            logger.warning("%s berth_code=%s field=max_draft_m", _INFERRED_BERTH_LIMIT_WARNING, bc_str)
            factor = settings.berth_limit_inference_factor
            spec.max_draft_m = ProvenanceField.from_history(
                spec.historical_max_draft_seen * factor,
                f"Derived conservatively from history max {spec.historical_max_draft_seen:.1f}m * {factor:.2f}"
            )

        # Equipment — always assumed for now (no data source)
        if not spec.equipment_types:
            spec.equipment_types = ["crane", "hose", "gangway"]
            spec.equipment_source = DataSource.ASSUMPTION

    return berths


# ── Full Port Master Builder ─────────────────────────────────────────────────

def build_port_master(
    port_name: str,
    port_code: str = "3779",
    berth_config_path: Optional[str | Path] = None,
    operational_capability_path: Optional[str | Path] = None,
    history_df: Optional[pd.DataFrame] = None,
) -> PortMaster:
    """
    Build a complete PortMaster from all available data sources.
    
    Priority: Spec > Operational > Historical
    
    Returns:
        PortMaster with fully enriched BerthSpec objects
    """
    berths: Dict[str, BerthSpec] = {}

    # 1. Load spec sheet (highest priority)
    if berth_config_path and Path(berth_config_path).exists():
        berths = ingest_berth_configurations(berth_config_path)
        logger.info(f"Loaded {len(berths)} berths from spec sheet")
    else:
        logger.warning("No berth configuration file — physical constraints will be YELLOW/RED quality")

    # 2. Enrich with operational capability
    if operational_capability_path and Path(operational_capability_path).exists():
        berths = ingest_operational_capability(operational_capability_path, berths)
        logger.info("Enriched berths with operational capability")
    else:
        logger.warning("No operational capability file — cargo/commodity data will be missing")

    # 3. Enrich with historical data (fallback)
    if history_df is not None and len(history_df) > 0:
        berths = enrich_from_history(berths, history_df)
        logger.info("Enriched berths with historical data")

    # 4. Score quality for each berth
    for bc, spec in berths.items():
        eq = score_berth_quality(spec)
        spec.quality_score = eq.overall_score
        spec.data_quality = eq.overall_gate

    # 5. Build PortMaster
    port = PortMaster(
        port_code=port_code,
        port_name=port_name,
        berths=berths,
        spec_loaded=berth_config_path is not None and Path(berth_config_path).exists(),
        operational_loaded=operational_capability_path is not None and Path(operational_capability_path).exists(),
        history_loaded=history_df is not None and len(history_df) > 0,
    )

    # Overall quality
    if berths:
        scores = [b.quality_score for b in berths.values()]
        port.quality_score = np.mean(scores)
        port.data_quality = QualityGate.GREEN if port.quality_score >= 80 else (
            QualityGate.YELLOW if port.quality_score >= 60 else QualityGate.RED
        )

    logger.info(f"Built PortMaster: {port.summary()}")
    return port


def save_port_master_config(port_master: PortMaster, output_path: str | Path):
    """Save port master as port_config.json (backward compatible + new fields)."""
    config = {
        "port_name": port_master.port_name,
        "port_code": port_master.port_code,
        "num_berths": len(port_master.berths),
        "data_quality": port_master.data_quality.value,
        "quality_score": round(port_master.quality_score, 1),
        "spec_loaded": port_master.spec_loaded,
        "operational_loaded": port_master.operational_loaded,
        "berths": [
            b.to_legacy_dict() for b in sorted(
                port_master.berths.values(),
                key=lambda x: x.berth_code,
            )
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)

    logger.info(f"Saved port config to {output_path}")
