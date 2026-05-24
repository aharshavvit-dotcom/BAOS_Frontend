"""
Assignment Tracker — Learning Engine.

Records completed assignment outcomes (predicted vs actual performance)
and provides historical success rates for vessel-type × berth combinations.

Storage: ports/<port>/learning/assignments.json
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


_PORTS_DIR = Path(__file__).resolve().parent.parent / "ports"


def _learning_path(port_name: str) -> Path:
    """Get path to learning data file for a port."""
    d = _PORTS_DIR / port_name / "learning"
    d.mkdir(parents=True, exist_ok=True)
    return d / "assignments.json"


def _load_records(port_name: str) -> List[dict]:
    """Load existing assignment records."""
    path = _learning_path(port_name)
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []
    return []


def _save_records(port_name: str, records: List[dict]):
    """Save assignment records."""
    path = _learning_path(port_name)
    with open(path, "w") as f:
        json.dump(records, f, indent=2, default=str)


def record_assignment(
    port_name: str,
    vessel_id: str,
    vessel_type: str,
    berth_code: str,
    predicted_wait_hours: float = 0.0,
    predicted_service_hours: float = 0.0,
    actual_wait_hours: Optional[float] = None,
    actual_service_hours: Optional[float] = None,
    confidence_at_assignment: float = 0.0,
    compatibility_score: float = 0.0,
    outcome: str = "completed",  # completed | cancelled | incident
    notes: str = "",
    spec_backed: bool = False,  # Phase 4: Was this decision backed by spec data?
    service_time_lower: float = 0.0,  # Phase 4: Quantile bounds
    service_time_upper: float = 0.0,
    delay_lower: float = 0.0,
    delay_upper: float = 0.0,
):
    """
    Record a completed assignment outcome for future learning.

    Args:
        port_name: Port identifier
        vessel_id: Vessel identifier
        vessel_type: Type of vessel
        berth_code: Berth where vessel was assigned
        predicted_wait_hours: ML-predicted wait at time of assignment
        predicted_service_hours: ML-predicted service time
        actual_wait_hours: Actual wait (None if not yet completed)
        actual_service_hours: Actual service time (None if not yet completed)
        confidence_at_assignment: Confidence score given at assignment time
        compatibility_score: Compatibility score at assignment time
        outcome: "completed", "cancelled", or "incident"
        notes: Any additional notes
        spec_backed: Whether constraint checks used spec data
        service_time_lower/upper: Quantile prediction bounds
        delay_lower/upper: Quantile prediction bounds
    """
    records = _load_records(port_name)

    # Compute prediction errors if actuals available
    svc_error = None
    wait_error = None
    within_bounds = None
    if actual_service_hours is not None and predicted_service_hours > 0:
        svc_error = round(actual_service_hours - predicted_service_hours, 2)
        if service_time_lower > 0 and service_time_upper > 0:
            within_bounds = service_time_lower <= actual_service_hours <= service_time_upper
    if actual_wait_hours is not None and predicted_wait_hours > 0:
        wait_error = round(actual_wait_hours - predicted_wait_hours, 2)

    records.append({
        "timestamp": datetime.utcnow().isoformat(),
        "vessel_id": vessel_id,
        "vessel_type": vessel_type,
        "berth_code": berth_code,
        "predicted_wait_hours": predicted_wait_hours,
        "predicted_service_hours": predicted_service_hours,
        "actual_wait_hours": actual_wait_hours,
        "actual_service_hours": actual_service_hours,
        "confidence_at_assignment": confidence_at_assignment,
        "compatibility_score": compatibility_score,
        "outcome": outcome,
        "notes": notes,
        "spec_backed": spec_backed,
        "service_time_lower": service_time_lower,
        "service_time_upper": service_time_upper,
        "delay_lower": delay_lower,
        "delay_upper": delay_upper,
        "service_error_h": svc_error,
        "wait_error_h": wait_error,
        "within_uncertainty_bounds": within_bounds,
    })
    _save_records(port_name, records)


def get_berth_performance(
    port_name: str,
    berth_code: Optional[str] = None,
) -> Dict[str, dict]:
    """
    Get performance summary per berth.

    Returns:
        {berth_code: {
            "total_assignments": int,
            "completed": int,
            "incidents": int,
            "avg_wait_hours": float,
            "avg_service_hours": float,
            "success_rate": float,  # 0-1
            "by_vessel_type": {type: {"count": int, "success_rate": float}}
        }}
    """
    records = _load_records(port_name)
    if not records:
        return {}

    berths: Dict[str, dict] = {}

    for r in records:
        bc = r.get("berth_code", "UNK")
        if berth_code and bc != berth_code:
            continue

        if bc not in berths:
            berths[bc] = {
                "total_assignments": 0,
                "completed": 0,
                "incidents": 0,
                "wait_hours_sum": 0.0,
                "service_hours_sum": 0.0,
                "by_vessel_type": {},
            }

        b = berths[bc]
        b["total_assignments"] += 1

        outcome = r.get("outcome", "completed")
        if outcome == "completed":
            b["completed"] += 1
        elif outcome == "incident":
            b["incidents"] += 1

        # Track actuals if available, else predicted
        wait = r.get("actual_wait_hours") or r.get("predicted_wait_hours", 0)
        svc = r.get("actual_service_hours") or r.get("predicted_service_hours", 0)
        if wait is not None:
            b["wait_hours_sum"] += float(wait)
        if svc is not None:
            b["service_hours_sum"] += float(svc)

        # By vessel type
        vt = r.get("vessel_type", "Unknown")
        if vt not in b["by_vessel_type"]:
            b["by_vessel_type"][vt] = {"count": 0, "completed": 0}
        b["by_vessel_type"][vt]["count"] += 1
        if outcome == "completed":
            b["by_vessel_type"][vt]["completed"] += 1

    # Compute averages and rates
    result = {}
    for bc, b in berths.items():
        total = b["total_assignments"]
        by_type = {}
        for vt, vt_data in b["by_vessel_type"].items():
            by_type[vt] = {
                "count": vt_data["count"],
                "success_rate": vt_data["completed"] / max(vt_data["count"], 1),
            }

        result[bc] = {
            "total_assignments": total,
            "completed": b["completed"],
            "incidents": b["incidents"],
            "avg_wait_hours": round(b["wait_hours_sum"] / max(total, 1), 1),
            "avg_service_hours": round(b["service_hours_sum"] / max(total, 1), 1),
            "success_rate": round(b["completed"] / max(total, 1), 3),
            "by_vessel_type": by_type,
        }

    return result


def get_compatibility_history(
    port_name: str,
    vessel_type: str,
    berth_code: str,
) -> Dict[str, float]:
    """
    Get historical success metrics for a specific vessel_type × berth combination.

    Returns:
        {
            "assignment_count": int,
            "success_rate": float (0-1),
            "avg_confidence": float,
            "avg_compatibility": float,
            "confidence_boost": float (-0.2 to +0.2),
        }
    """
    records = _load_records(port_name)
    matching = [
        r for r in records
        if r.get("vessel_type", "").lower() == vessel_type.lower()
        and r.get("berth_code", "") == berth_code
    ]

    if not matching:
        return {
            "assignment_count": 0,
            "success_rate": 0.5,  # Unknown
            "avg_confidence": 0.0,
            "avg_compatibility": 0.0,
            "confidence_boost": 0.0,  # Neutral
        }

    completed = sum(1 for r in matching if r.get("outcome") == "completed")
    incidents = sum(1 for r in matching if r.get("outcome") == "incident")
    total = len(matching)

    success_rate = completed / max(total, 1)
    avg_conf = sum(r.get("confidence_at_assignment", 0) for r in matching) / total
    avg_compat = sum(r.get("compatibility_score", 0) for r in matching) / total

    # Confidence boost: +0.1 for each 10% above 80% success, -0.1 for each 10% below 50%
    if success_rate >= 0.9:
        boost = 0.15
    elif success_rate >= 0.8:
        boost = 0.10
    elif success_rate >= 0.6:
        boost = 0.0
    elif success_rate >= 0.4:
        boost = -0.10
    else:
        boost = -0.20

    return {
        "assignment_count": total,
        "success_rate": round(success_rate, 3),
        "avg_confidence": round(avg_conf, 1),
        "avg_compatibility": round(avg_compat, 1),
        "confidence_boost": boost,
    }


def get_prediction_accuracy(
    port_name: str,
) -> Dict[str, float]:
    """
    Compute prediction accuracy metrics for model calibration.

    Returns:
        {
            "total_with_actuals": int,
            "service_mae_h": float,
            "wait_mae_h": float,
            "within_bounds_pct": float,  # % of actuals within P25-P75
            "spec_backed_pct": float,    # % of decisions using spec data
            "avg_confidence_calibration": float,  # correlation of confidence vs success
        }
    """
    records = _load_records(port_name)
    if not records:
        return {"total_with_actuals": 0}

    svc_errors = []
    wait_errors = []
    bounds_results = []
    spec_count = 0

    for r in records:
        if r.get("service_error_h") is not None:
            svc_errors.append(abs(r["service_error_h"]))
        if r.get("wait_error_h") is not None:
            wait_errors.append(abs(r["wait_error_h"]))
        if r.get("within_uncertainty_bounds") is not None:
            bounds_results.append(1 if r["within_uncertainty_bounds"] else 0)
        if r.get("spec_backed"):
            spec_count += 1

    total = max(len(svc_errors), len(wait_errors), 1)

    return {
        "total_with_actuals": total,
        "service_mae_h": round(sum(svc_errors) / max(len(svc_errors), 1), 2) if svc_errors else None,
        "wait_mae_h": round(sum(wait_errors) / max(len(wait_errors), 1), 2) if wait_errors else None,
        "within_bounds_pct": round(
            sum(bounds_results) / max(len(bounds_results), 1) * 100, 1
        ) if bounds_results else None,
        "spec_backed_pct": round(spec_count / max(len(records), 1) * 100, 1),
    }
