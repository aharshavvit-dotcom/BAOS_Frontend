"""
Data Validators — validation rules for ingested port call data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# Outlier thresholds (configurable)
MAX_BERTH_OCCUPANCY_HOURS = 720  # 30 days
MAX_PILOT_WAIT_HOURS = 168  # 7 days
MAX_TOTAL_PORT_STAY_HOURS = 1440  # 60 days


@dataclass
class ValidationResult:
    is_valid: bool = True
    is_valid_for_training: bool = True
    status: str = "VALID"
    notes: List[str] = field(default_factory=list)


def validate_port_call_row(row: dict) -> ValidationResult:
    """
    Validate a single port call row.

    Checks:
    - Physical dimensions positive
    - Timestamp ordering logical
    - Duration sanity
    - Outlier detection

    Returns a ValidationResult (never deletes, only flags).
    """
    result = ValidationResult()

    # ── Physical dimension checks ────────────────────────────
    loa = _safe_float(row.get("loa_m"))
    beam = _safe_float(row.get("beam_m"))
    draft = _safe_float(row.get("arrival_draft_m"))

    if loa is not None and loa <= 0:
        result.notes.append("LOA <= 0")
        result.is_valid_for_training = False

    if beam is not None and beam <= 0:
        result.notes.append("Beam <= 0")

    if draft is not None and draft <= 0:
        result.notes.append("Draft <= 0")

    # ── Timestamp ordering ───────────────────────────────────
    eosp = _safe_ts(row.get("eosp_ts"))
    pob = _safe_ts(row.get("pob_ts"))
    all_fast = _safe_ts(row.get("all_fast_ts"))
    last_line = _safe_ts(row.get("last_line_ts"))
    cosp = _safe_ts(row.get("cosp_ts"))

    if pob and all_fast and all_fast < pob:
        result.notes.append("ALL_FAST < POB (timestamp order violation)")
        result.is_valid_for_training = False

    if all_fast and last_line and last_line < all_fast:
        result.notes.append("LAST_LINE < ALL_FAST (timestamp order violation)")
        result.is_valid_for_training = False

    if last_line and cosp and cosp < last_line:
        result.notes.append("COSP < LAST_LINE (timestamp order violation)")
        result.is_valid_for_training = False

    # ── Duration checks ──────────────────────────────────────
    berth_hours = _safe_float(row.get("berth_occupancy_hours"))
    pilot_wait = _safe_float(row.get("pilot_wait_hours"))
    total_stay = _safe_float(row.get("total_port_stay_hours"))

    if berth_hours is not None and berth_hours < 0:
        result.notes.append("Negative berth occupancy")
        result.is_valid_for_training = False

    if total_stay is not None and total_stay < 0:
        result.notes.append("Negative total port stay")
        result.is_valid_for_training = False

    # ── Outlier detection ────────────────────────────────────
    if berth_hours is not None and berth_hours > MAX_BERTH_OCCUPANCY_HOURS:
        result.notes.append(f"Service time exceeds max threshold ({berth_hours:.1f}h > {MAX_BERTH_OCCUPANCY_HOURS}h)")
        result.is_valid_for_training = False
        result.status = "OUTLIER"

    if pilot_wait is not None and pilot_wait > MAX_PILOT_WAIT_HOURS:
        result.notes.append(f"Pilot wait exceeds max threshold ({pilot_wait:.1f}h > {MAX_PILOT_WAIT_HOURS}h)")
        result.is_valid_for_training = False
        result.status = "OUTLIER"

    if total_stay is not None and total_stay > MAX_TOTAL_PORT_STAY_HOURS:
        result.notes.append(f"Total port stay exceeds max threshold ({total_stay:.1f}h > {MAX_TOTAL_PORT_STAY_HOURS}h)")
        result.is_valid_for_training = False
        result.status = "OUTLIER"

    # Determine final validity
    if not result.is_valid_for_training and result.status == "VALID":
        result.status = "INVALID"

    if result.notes:
        result.is_valid = False

    return result


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        import math
        f = float(val)
        return f if not math.isnan(f) else None
    except (ValueError, TypeError):
        return None


def _safe_ts(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        import pandas as pd
        ts = pd.to_datetime(val, errors="coerce")
        return ts.to_pydatetime() if not pd.isna(ts) else None
    except Exception:
        return None
