"""
Feature Builder — Training Engine Layer 2
Builds feature vectors from vessel + port state for ML models.
Handles both training (historical) and inference (real-time) scenarios.

Phase 2 Enhancements:
  - Cyclical time encoding (sin/cos for hour, day)
  - Equipment match score from vessel_type_knowledge
  - Berth specialization ratio (% of vessel type at berth)
  - Cargo handling rate features
  - Spec-aware berth quality features
  - Beam dimension added to vessel features
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Feature Column Groups ───────────────────────────────────────────────────
VESSEL_FEATURES = [
    "loa", "adraft", "ddraught", "dwt", "beam",
]
CONTEXT_FEATURES = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "month_sin", "month_cos",
    "congestion_level",
]
BERTH_FEATURES = [
    "berth_depth_m", "berth_max_loa_m", "berth_max_draft_m", "berth_max_beam_m",
]
DERIVED_FEATURES = [
    "loa_berth_ratio", "draft_depth_ratio", "beam_berth_ratio",
    "is_large_vessel",
    "historical_svc_median",
    "equipment_match_score",
    "berth_specialization_ratio",
    "cargo_handling_rate",
]


def _safe_numeric(series, default=0.0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _cyclical_encode(values: pd.Series, period: float) -> Tuple[pd.Series, pd.Series]:
    """Encode a periodic feature as sin/cos pair."""
    radians = 2 * np.pi * values / period
    return np.sin(radians), np.cos(radians)


def _compute_equipment_match(vessel_type: str, berth_equipment: list) -> float:
    """Compute equipment match score (0-100) using vessel_type_knowledge."""
    try:
        from optimization_engine.vessel_type_knowledge import compute_compatibility_score
        score, _, _ = compute_compatibility_score(
            vessel_type, "", berth_equipment, [],
        )
        return float(score)
    except Exception:
        return 65.0  # Moderate default


def _compute_berth_specialization(
    berth_code: str, vessel_type: str, df: pd.DataFrame,
    berth_col: str, vt_col: str,
) -> float:
    """Historical % of a vessel type at a specific berth (0-1)."""
    if not vessel_type or not berth_code:
        return 0.0
    berth_mask = df[berth_col].astype(str) == str(berth_code)
    berth_total = berth_mask.sum()
    if berth_total == 0:
        return 0.0
    vt_lower = vessel_type.lower().strip()
    type_at_berth = (
        berth_mask & (df[vt_col].astype(str).str.lower().str.strip() == vt_lower)
    ).sum()
    return type_at_berth / berth_total


def build_training_features(
    df_history: pd.DataFrame,
    port_config: dict,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Build feature matrix from historical data.
    Returns (X, y_berth, y_service_time, y_delay)
    """
    df = df_history.copy()

    # Build berth lookup
    berth_info = {}
    for b in port_config.get("berths", []):
        berth_info[str(b["berth_code"])] = b

    # Service time stats
    svc_stats = {}
    for rec in port_config.get("service_time_stats", []):
        key = (str(rec.get("berth_code", "")), str(rec.get("vessel_type", "")))
        svc_stats[key] = rec.get("service_hours_median", 12.0)

    # ── Vessel Features ──────────────────────────────────────────────
    df["loa"] = _safe_numeric(df.get("loa", pd.Series(dtype=float)))
    df["adraft"] = _safe_numeric(df.get("adraft", pd.Series(dtype=float)))
    df["ddraught"] = _safe_numeric(df.get("ddraught", df.get("adraft", pd.Series(dtype=float))))
    df["dwt"] = _safe_numeric(df.get("dwt", pd.Series(dtype=float)))

    # Beam — new in Phase 2
    beam_col = None
    for candidate in ["beam", "breadth", "width"]:
        if candidate in df.columns:
            beam_col = candidate
            break
    if beam_col:
        df["beam"] = _safe_numeric(df[beam_col])
    else:
        # Estimate beam from LOA using typical L/B ratio (~6.5 for cargo ships)
        df["beam"] = (df["loa"] / 6.5).clip(lower=0, upper=70)

    # Target: berth code
    berth_col = "berthcode" if "berthcode" in df.columns else "berth_code"
    if berth_col not in df.columns:
        raise ValueError("No berth column found in history")
    df["target_berth"] = df[berth_col].astype(str)

    # Target: service time
    df["berth_occupancy_h"] = _safe_numeric(df.get("berth_occupancy_h", pd.Series(dtype=float)))

    # Target: delay (pilot wait)
    df["pilot_wait_h"] = _safe_numeric(df.get("pilot_wait_h", pd.Series(dtype=float)))

    # Vessel type column
    vt_col = "vesseltype" if "vesseltype" in df.columns else "vessel_type"
    has_vt = vt_col in df.columns

    # Vessel type encoding — keep top 10 as dummies
    if has_vt:
        vt_dummies = pd.get_dummies(df[vt_col].astype(str).str.strip(), prefix="vt")
        top_cols = vt_dummies.sum().nlargest(10).index.tolist()
        vt_dummies = vt_dummies[top_cols]
    else:
        vt_dummies = pd.DataFrame(index=df.index)

    # ── Cyclical Time Features ───────────────────────────────────────
    time_col = None
    for tc in ["eta", "eosp", "pob", "all_fast"]:
        if tc in df.columns:
            time_col = tc
            break
    if time_col:
        ts = pd.to_datetime(df[time_col], errors="coerce")
        hour = ts.dt.hour.fillna(12).astype(float)
        dow = ts.dt.dayofweek.fillna(3).astype(float)
        month = ts.dt.month.fillna(6).astype(float)
    else:
        hour = pd.Series(12.0, index=df.index)
        dow = pd.Series(3.0, index=df.index)
        month = pd.Series(6.0, index=df.index)

    df["hour_sin"], df["hour_cos"] = _cyclical_encode(hour, 24.0)
    df["dow_sin"], df["dow_cos"] = _cyclical_encode(dow, 7.0)
    df["month_sin"], df["month_cos"] = _cyclical_encode(month, 12.0)

    # Congestion: count of vessels berthing same day
    if time_col:
        ts = pd.to_datetime(df[time_col], errors="coerce")
        daily_counts = ts.dt.date.value_counts()
        df["congestion_level"] = ts.dt.date.map(daily_counts).fillna(1).astype(int)
    else:
        df["congestion_level"] = 5

    # ── Berth-Specific Features ──────────────────────────────────────
    def get_berth_feat(row, feat, default):
        bi = berth_info.get(str(row.get("target_berth", "")), {})
        return bi.get(feat, default)

    df["berth_depth_m"] = df.apply(lambda r: get_berth_feat(r, "depth_m", 12.0), axis=1)
    df["berth_max_loa_m"] = df.apply(lambda r: get_berth_feat(r, "max_loa_m", 300.0), axis=1)
    df["berth_max_draft_m"] = df.apply(lambda r: get_berth_feat(r, "max_draft_m", 15.0), axis=1)
    df["berth_max_beam_m"] = df.apply(lambda r: get_berth_feat(r, "max_beam_m", 50.0), axis=1)

    # ── Derived Features ─────────────────────────────────────────────
    df["loa_berth_ratio"] = df["loa"] / df["berth_max_loa_m"].replace(0, 300)
    df["draft_depth_ratio"] = df["adraft"] / df["berth_depth_m"].replace(0, 12)
    df["beam_berth_ratio"] = df["beam"] / df["berth_max_beam_m"].replace(0, 50)
    df["is_large_vessel"] = (df["loa"] > 200).astype(int)

    # Historical service time median for berth+type combo
    vt_vals = df[vt_col].astype(str) if has_vt else pd.Series("", index=df.index)
    df["historical_svc_median"] = [
        svc_stats.get((str(r.get("target_berth", "")), str(vt_vals.iloc[i])), 12.0)
        for i, (_, r) in enumerate(df.iterrows())
    ]

    # Equipment match score — using vessel_type_knowledge
    equip_scores = []
    for _, row in df.iterrows():
        vt = str(vt_vals.iloc[_]) if has_vt and _ < len(vt_vals) else ""
        bi = berth_info.get(str(row.get("target_berth", "")), {})
        equip = bi.get("equipment", [])
        equip_scores.append(_compute_equipment_match(vt, equip))
    df["equipment_match_score"] = equip_scores

    # Berth specialization ratio — how often does this vessel type use this berth?
    if has_vt:
        spec_ratios = []
        for _, row in df.iterrows():
            bc = str(row.get("target_berth", ""))
            vt = str(vt_vals.iloc[_]) if _ < len(vt_vals) else ""
            spec_ratios.append(
                _compute_berth_specialization(bc, vt, df, berth_col, vt_col)
            )
        df["berth_specialization_ratio"] = spec_ratios
    else:
        df["berth_specialization_ratio"] = 0.0

    # Cargo handling rate — cargo_tons / avg_service_time
    cargo_col = None
    for c in ["cargo_qty", "cargo_tons", "cargo_quantity", "dwt"]:
        if c in df.columns:
            cargo_col = c
            break
    if cargo_col and df["berth_occupancy_h"].mean() > 0:
        cargo_vals = _safe_numeric(df[cargo_col])
        avg_svc = df["berth_occupancy_h"].replace(0, 12).clip(lower=0.5)
        df["cargo_handling_rate"] = (cargo_vals / avg_svc).clip(lower=0, upper=50000)
    else:
        df["cargo_handling_rate"] = 0.0

    # ── Build X Matrix ───────────────────────────────────────────────
    feature_cols = VESSEL_FEATURES + CONTEXT_FEATURES + BERTH_FEATURES + DERIVED_FEATURES
    X = df[feature_cols].copy()
    for c in vt_dummies.columns:
        X[c] = vt_dummies[c].values

    # Fill NaN
    X = X.fillna(0)

    # Targets
    y_berth = df["target_berth"]
    y_service = df["berth_occupancy_h"].clip(lower=0.5, upper=500)
    y_delay = df["pilot_wait_h"].clip(lower=0, upper=100)

    # Drop rows with invalid targets
    valid = y_berth.notna() & (y_berth != "") & (y_berth != "nan")
    X = X[valid].reset_index(drop=True)
    y_berth = y_berth[valid].reset_index(drop=True)
    y_service = y_service[valid].reset_index(drop=True)
    y_delay = y_delay[valid].reset_index(drop=True)

    return X, y_berth, y_service, y_delay


def build_inference_features(
    vessel: dict,
    berth_info: dict,
    port_config: dict,
    congestion: int = 5,
) -> pd.DataFrame:
    """
    Build feature vector for a single vessel against a specific berth.
    Used during real-time inference. Feature set matches training features.
    """
    from datetime import datetime as dt

    eta = pd.to_datetime(vessel.get("eta", dt.now()))

    # Service time stats lookup
    svc_stats = {}
    for rec in port_config.get("service_time_stats", []):
        key = (str(rec.get("berth_code", "")), str(rec.get("vessel_type", "")))
        svc_stats[key] = rec.get("service_hours_median", 12.0)

    # Equipment match score
    vessel_type = str(vessel.get("vessel_type", ""))
    berth_equip = berth_info.get("equipment", [])
    equip_score = _compute_equipment_match(vessel_type, berth_equip)

    # Berth specialization from stats
    berth_spec_ratio = berth_info.get("specialization_ratio", 0.0)

    # Cargo handling rate
    cargo_tons = float(vessel.get("cargo_tons", vessel.get("dwt", 0)))
    avg_svc = svc_stats.get(
        (str(berth_info.get("berth_code", "")), vessel_type),
        12.0,
    )
    cargo_rate = cargo_tons / max(avg_svc, 0.5) if cargo_tons > 0 else 0.0

    loa = float(vessel.get("loa", 0))
    draft = float(vessel.get("draft", vessel.get("adraft", 0)))
    beam = float(vessel.get("beam", loa / 6.5 if loa > 0 else 0))
    max_loa = berth_info.get("max_loa_m", 300.0)
    depth = berth_info.get("depth_m", 12.0)
    max_beam = berth_info.get("max_beam_m", 50.0)

    # Cyclical time encoding
    hour_sin, hour_cos = np.sin(2 * np.pi * eta.hour / 24), np.cos(2 * np.pi * eta.hour / 24)
    dow_sin, dow_cos = np.sin(2 * np.pi * eta.dayofweek / 7), np.cos(2 * np.pi * eta.dayofweek / 7)
    month_sin, month_cos = np.sin(2 * np.pi * eta.month / 12), np.cos(2 * np.pi * eta.month / 12)

    row = {
        # Vessel features
        "loa": loa,
        "adraft": draft,
        "ddraught": float(vessel.get("ddraught", draft)),
        "dwt": float(vessel.get("dwt", 0)),
        "beam": beam,
        # Context features
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "dow_sin": dow_sin,
        "dow_cos": dow_cos,
        "month_sin": month_sin,
        "month_cos": month_cos,
        "congestion_level": congestion,
        # Berth features
        "berth_depth_m": depth,
        "berth_max_loa_m": max_loa,
        "berth_max_draft_m": berth_info.get("max_draft_m", 15.0),
        "berth_max_beam_m": max_beam,
        # Derived features
        "loa_berth_ratio": loa / max(max_loa, 1),
        "draft_depth_ratio": draft / max(depth, 1),
        "beam_berth_ratio": beam / max(max_beam, 1),
        "is_large_vessel": 1 if loa > 200 else 0,
        "historical_svc_median": svc_stats.get(
            (str(berth_info.get("berth_code", "")), vessel_type),
            12.0,
        ),
        "equipment_match_score": equip_score,
        "berth_specialization_ratio": berth_spec_ratio,
        "cargo_handling_rate": min(cargo_rate, 50000),
    }

    # Add vessel type dummy column to match training features
    if vessel_type:
        vt_clean = str(vessel_type).lower().strip()
        row[f"vt_{vt_clean}"] = 1

    return pd.DataFrame([row])
