"""
Pattern Discovery Engine — Training Engine Layer 2.5

Analyzes historical port-call data to discover allocation patterns:
  - Specialization scores: P(berth | vessel_type) and P(vessel_type | berth)
  - Factor importance: which features most predict berth selection
  - Constraint detection: hard safety rules and soft preferences
  - Berth characteristics: composition, avg turnaround, flexibility

Output artifact: ports/{port}/models/patterns.json
"""
from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.db.repositories.port_store import load_history, load_port_config, get_models_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_patterns(port_name: str) -> Dict[str, Any]:
    """
    Run the full pattern discovery pipeline for a port.

    Steps:
        1. Load historical data
        2. Compute specialization scores
        3. Rank factor importance
        4. Detect hard/soft constraints
        5. Profile berth characteristics
        6. Save patterns.json

    Returns the patterns dict.
    """
    df = load_history(port_name)
    port_config = load_port_config(port_name)

    # Normalize column names
    berth_col = _find_col(df, ["berthcode", "berth_code"])
    vtype_col = _find_col(df, ["vesseltype", "vessel_type"])
    svc_col = _find_col(df, ["berth_occupancy_h", "service_hours"])
    loa_col = _find_col(df, ["loa"])
    draft_col = _find_col(df, ["adraft", "draft"])

    if not berth_col or not vtype_col:
        logger.warning("Missing berth or vessel-type column; returning empty patterns")
        return {}

    df["_berth"] = df[berth_col].astype(str).str.strip()
    df["_vtype"] = df[vtype_col].astype(str).str.strip()

    # Compute all pattern dimensions
    specialization = _compute_specialization(df)
    factor_importance = _compute_factor_importance(df, berth_col, vtype_col, loa_col, draft_col)
    constraints = _detect_constraints(df, specialization)
    berth_chars = _profile_berths(df, svc_col)

    patterns: Dict[str, Any] = {
        "port": port_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_records": len(df),
        "specialization_scores": specialization,
        "factor_importance": factor_importance,
        "constraints": constraints,
        "berth_characteristics": berth_chars,
    }

    # Save artifact
    models_dir = get_models_dir(port_name)
    out_path = models_dir / "patterns.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2, default=_json_default)
    logger.info("Saved patterns.json to %s (%d records analyzed)", out_path, len(df))

    return patterns


def load_patterns(port_name: str) -> Optional[Dict[str, Any]]:
    """Load pre-computed patterns.json, or None if not available."""
    models_dir = get_models_dir(port_name)
    path = models_dir / "patterns.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Specialization scores
# ---------------------------------------------------------------------------

def _compute_specialization(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    For each vessel type, compute how specialized each berth is.

    Two measures combined:
      - freq(berth | vessel_type): fraction of this vessel_type going to berth
      - composition(vessel_type | berth): fraction of berth occupied by this type

    Final score = 0.6 * freq + 0.4 * composition  (0–1.0)
    """
    vtypes = df["_vtype"].unique()
    berths = df["_berth"].unique()

    # Count matrices
    vt_counts = df.groupby("_vtype").size()              # total per vessel type
    berth_counts = df.groupby("_berth").size()            # total per berth
    pair_counts = df.groupby(["_vtype", "_berth"]).size() # (vtype, berth) counts

    result: Dict[str, Dict[str, float]] = {}
    for vt in vtypes:
        vt_total = vt_counts.get(vt, 0)
        if vt_total == 0:
            continue
        scores: Dict[str, float] = {}
        for b in berths:
            count = pair_counts.get((vt, b), 0)
            if count == 0:
                scores[b] = 0.0
                continue
            freq = count / vt_total                   # P(berth | vtype)
            b_total = berth_counts.get(b, 1)
            composition = count / b_total             # P(vtype | berth)
            scores[b] = round(0.6 * freq + 0.4 * composition, 4)
        result[vt] = scores

    return result


# ---------------------------------------------------------------------------
# Factor importance
# ---------------------------------------------------------------------------

def _compute_factor_importance(
    df: pd.DataFrame,
    berth_col: str,
    vtype_col: str,
    loa_col: Optional[str],
    draft_col: Optional[str],
) -> Dict[str, float]:
    """
    Estimate how much each factor predicts berth allocation.

    Uses within-group variance ratio (eta-squared) for numeric features
    and Cramér's V for categorical features.
    """
    importance: Dict[str, float] = {}
    target = df[berth_col].astype(str)

    # Vessel type — Cramér's V
    if vtype_col and vtype_col in df.columns:
        importance["vessel_type"] = _cramers_v(df[vtype_col].astype(str), target)

    # LOA — eta-squared
    if loa_col and loa_col in df.columns:
        importance["loa"] = _eta_squared(pd.to_numeric(df[loa_col], errors="coerce"), target)

    # Draft — eta-squared
    if draft_col and draft_col in df.columns:
        importance["draft"] = _eta_squared(pd.to_numeric(df[draft_col], errors="coerce"), target)

    # DWT
    dwt_col = _find_col(df, ["dwt"])
    if dwt_col:
        importance["dwt"] = _eta_squared(pd.to_numeric(df[dwt_col], errors="coerce"), target)

    # Equipment (binary: present or not) — low default
    importance.setdefault("equipment", 0.05)

    # Normalize to sum ~1.0
    total = sum(importance.values()) or 1.0
    importance = {k: round(v / total, 3) for k, v in importance.items()}

    return importance


def _eta_squared(numeric_series: pd.Series, groups: pd.Series) -> float:
    """Eta-squared: ratio of between-group to total variance."""
    valid = numeric_series.dropna()
    groups_aligned = groups.loc[valid.index]
    grand_mean = valid.mean()
    ss_total = ((valid - grand_mean) ** 2).sum()
    if ss_total == 0:
        return 0.0
    group_means = valid.groupby(groups_aligned).transform("mean")
    ss_between = ((group_means - grand_mean) ** 2).sum()
    return float(min(ss_between / ss_total, 1.0))


def _cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Cramér's V for two categorical variables."""
    try:
        ct = pd.crosstab(x, y)
        n = ct.values.sum()
        if n == 0:
            return 0.0
        chi2 = 0.0
        row_sums = ct.sum(axis=1).values
        col_sums = ct.sum(axis=0).values
        for i in range(ct.shape[0]):
            for j in range(ct.shape[1]):
                expected = row_sums[i] * col_sums[j] / n
                if expected > 0:
                    chi2 += (ct.iloc[i, j] - expected) ** 2 / expected
        k = min(ct.shape[0], ct.shape[1])
        if k <= 1:
            return 0.0
        return float(min(np.sqrt(chi2 / (n * (k - 1))), 1.0))
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Constraint detection
# ---------------------------------------------------------------------------

def _detect_constraints(
    df: pd.DataFrame,
    specialization: Dict[str, Dict[str, float]],
) -> List[Dict[str, str]]:
    """
    Auto-detect constraints from observed data.

    Rules:
      - If a vessel_type uses a berth set exclusively (>90%),
        and no other types use those berths → HARD constraint
      - If a vessel_type strongly prefers certain berths (>70%) → SOFT constraint
      - If a berth never handles a vessel_type → implicit exclusion
    """
    constraints: List[Dict[str, str]] = []
    berths_by_vtype: Dict[str, set] = defaultdict(set)

    for vt, scores in specialization.items():
        top_berths = [b for b, s in scores.items() if s >= 0.15]
        exclusive_berths = [b for b, s in scores.items() if s >= 0.40]
        berths_by_vtype[vt] = set(top_berths)

        # Check if this type is highly concentrated
        total_score = sum(scores.values())
        top_score = sum(sorted(scores.values(), reverse=True)[:3])
        concentration = top_score / total_score if total_score > 0 else 0

        if concentration > 0.90 and exclusive_berths:
            # Check if the exclusive berths are dominated by this type
            constraints.append({
                "type": "hard",
                "vessel_type": vt,
                "berths": ", ".join(exclusive_berths),
                "rule": f"MUST_USE_{exclusive_berths[0].split(' ')[0].upper()}",
                "reason": f"{vt} vessels concentrated ({concentration:.0%}) in {', '.join(exclusive_berths)}",
                "confidence": f"{concentration:.2f}",
            })
        elif concentration > 0.70 and top_berths:
            constraints.append({
                "type": "soft",
                "vessel_type": vt,
                "berths": ", ".join(top_berths),
                "rule": f"PREFER_{top_berths[0].split(' ')[0].upper()}",
                "reason": f"{vt} vessels prefer ({concentration:.0%}) these berths",
                "confidence": f"{concentration:.2f}",
            })

    # Cross-type exclusions: berths that NEVER handle a type
    all_berths = set()
    for scores in specialization.values():
        all_berths.update(scores.keys())

    for vt, scores in specialization.items():
        excluded = [b for b in all_berths if scores.get(b, 0) == 0]
        if excluded and len(excluded) < len(all_berths):
            constraints.append({
                "type": "exclusion",
                "vessel_type": vt,
                "berths": ", ".join(sorted(excluded)[:5]),
                "rule": "NEVER_OBSERVED",
                "reason": f"{vt} never assigned to these berths historically",
            })

    return constraints


# ---------------------------------------------------------------------------
# Berth characteristics
# ---------------------------------------------------------------------------

def _profile_berths(
    df: pd.DataFrame,
    svc_col: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """
    Profile each berth: composition, avg turnaround, specialization label.
    """
    result: Dict[str, Dict[str, Any]] = {}
    berths = df["_berth"].unique()

    for b in berths:
        subset = df[df["_berth"] == b]
        total = len(subset)
        if total == 0:
            continue

        # Composition: vessel type mix
        composition = (
            subset["_vtype"].value_counts(normalize=True)
            .round(4)
            .to_dict()
        )

        # Dominant type
        dominant_type = max(composition, key=composition.get) if composition else "Unknown"
        dominant_pct = composition.get(dominant_type, 0)

        # Avg turnaround
        avg_turnaround = None
        if svc_col and svc_col in df.columns:
            svc_values = pd.to_numeric(subset[svc_col], errors="coerce").dropna()
            if len(svc_values) > 0:
                avg_turnaround = round(float(svc_values.mean()), 1)

        # Flexibility: number of distinct vessel types handled
        n_types = subset["_vtype"].nunique()
        if dominant_pct > 0.85:
            flexibility = "highly_specialized"
        elif dominant_pct > 0.60:
            flexibility = "moderately_specialized"
        else:
            flexibility = "flexible"

        result[b] = {
            "total_assignments": total,
            "dominant_type": dominant_type,
            "dominant_pct": dominant_pct,
            "composition": composition,
            "avg_turnaround_h": avg_turnaround,
            "vessel_types_handled": n_types,
            "flexibility": flexibility,
        }

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find the first matching column name (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


def _json_default(obj: Any) -> Any:
    """JSON serializer for numpy/pandas types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return str(obj)
