"""
Port Call Repository — Queries for baos.port_call.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.baos_models import BaosPortCall, BaosPort


async def get_training_rows(
    db: AsyncSession,
    port_code: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[BaosPortCall]:
    """Return port calls valid for ML training."""
    q = (
        select(BaosPortCall)
        .join(BaosPort, BaosPortCall.port_id == BaosPort.port_id)
        .where(
            BaosPort.port_code == port_code,
            BaosPortCall.is_valid_for_training == True,  # noqa: E712
        )
    )
    if start_date:
        q = q.where(BaosPortCall.eosp_ts >= start_date)
    if end_date:
        q = q.where(BaosPortCall.eosp_ts <= end_date)
    q = q.order_by(BaosPortCall.eosp_ts)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_historical_service_medians(
    db: AsyncSession,
    port_code: str,
) -> List[Dict[str, Any]]:
    """Return median service times grouped by berth_code + vessel_type."""
    q = (
        select(
            BaosPortCall.berth_code_raw,
            BaosPortCall.vessel_type,
            func.count(BaosPortCall.port_call_id).label("count"),
            func.avg(BaosPortCall.berth_occupancy_hours).label("avg_hours"),
        )
        .join(BaosPort, BaosPortCall.port_id == BaosPort.port_id)
        .where(
            BaosPort.port_code == port_code,
            BaosPortCall.is_valid_for_training == True,  # noqa: E712
            BaosPortCall.berth_occupancy_hours > 0,
        )
        .group_by(BaosPortCall.berth_code_raw, BaosPortCall.vessel_type)
        .order_by(BaosPortCall.berth_code_raw, BaosPortCall.vessel_type)
    )
    result = await db.execute(q)
    return [
        {
            "berth_code": row.berth_code_raw,
            "vessel_type": row.vessel_type,
            "count": row.count,
            "avg_hours": round(float(row.avg_hours), 2) if row.avg_hours else 0,
        }
        for row in result.all()
    ]


async def get_port_call_stats(
    db: AsyncSession,
    port_code: str,
) -> Dict[str, Any]:
    """Return summary statistics for port calls."""
    q = (
        select(
            func.count(BaosPortCall.port_call_id).label("total"),
            func.count(
                BaosPortCall.port_call_id
            ).filter(BaosPortCall.is_valid_for_training == True).label("valid"),  # noqa: E712
            func.count(
                BaosPortCall.port_call_id
            ).filter(BaosPortCall.validation_status == "OUTLIER").label("outlier"),
            func.avg(BaosPortCall.berth_occupancy_hours).label("avg_berth_hours"),
            func.avg(BaosPortCall.total_port_stay_hours).label("avg_stay_hours"),
            func.avg(BaosPortCall.pilot_wait_hours).label("avg_pilot_wait"),
        )
        .join(BaosPort, BaosPortCall.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
    )
    result = await db.execute(q)
    row = result.one_or_none()
    if not row:
        return {"total": 0, "valid": 0, "outlier": 0}
    return {
        "total": row.total or 0,
        "valid": row.valid or 0,
        "outlier": row.outlier or 0,
        "avg_berth_hours": round(float(row.avg_berth_hours), 2) if row.avg_berth_hours else 0,
        "avg_stay_hours": round(float(row.avg_stay_hours), 2) if row.avg_stay_hours else 0,
        "avg_pilot_wait": round(float(row.avg_pilot_wait), 2) if row.avg_pilot_wait else 0,
    }
