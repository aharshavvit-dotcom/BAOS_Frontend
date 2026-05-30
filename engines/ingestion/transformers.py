"""
Transformers — staging-to-canonical transformation logic.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def safe_float(val, default: float = None) -> Optional[float]:
    """Safely convert to float, returning default for non-numeric values."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    s = str(val).strip()
    if s.lower() in ("no restrictions", "", "nan", "none", "n/a", "-"):
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def safe_datetime(val) -> Optional[datetime]:
    """Safely convert to datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        ts = pd.to_datetime(val, errors="coerce")
        return ts.to_pydatetime() if not pd.isna(ts) else None
    except Exception:
        return None


def compute_derived_durations(row: dict) -> dict:
    """
    Compute KPI durations from timestamps.

    pilot_wait_hours        = POB - EOSP
    pilot_to_berth_hours    = ALL_FAST - POB
    berth_occupancy_hours   = LAST_LINE - ALL_FAST
    unberth_outbound_hours  = COSP - LAST_LINE
    total_port_stay_hours   = COSP - EOSP
    """
    eosp = safe_datetime(row.get("eosp_ts"))
    pob = safe_datetime(row.get("pob_ts"))
    all_fast = safe_datetime(row.get("all_fast_ts"))
    last_line = safe_datetime(row.get("last_line_ts"))
    cosp = safe_datetime(row.get("cosp_ts"))

    def hours_between(a, b):
        if a and b:
            return (b - a).total_seconds() / 3600.0
        return None

    return {
        "pilot_wait_hours": hours_between(eosp, pob),
        "pilot_to_berth_hours": hours_between(pob, all_fast),
        "berth_occupancy_hours": hours_between(all_fast, last_line),
        "unberth_outbound_hours": hours_between(last_line, cosp),
        "total_port_stay_hours": hours_between(eosp, cosp),
    }
