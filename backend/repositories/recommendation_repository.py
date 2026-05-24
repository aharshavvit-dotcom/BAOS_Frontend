"""
Recommendation Repository — CRUD for baos.recommendation_log.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.baos_models import BaosRecommendationLog, BaosPort


async def save_recommendation_log(
    db: AsyncSession,
    port_id: UUID,
    vessel_payload: dict,
    recommendations: dict,
    assumptions_used: dict = None,
    model_versions: dict = None,
) -> BaosRecommendationLog:
    """Save a recommendation log entry."""
    log = BaosRecommendationLog(
        port_id=port_id,
        vessel_payload=vessel_payload,
        recommendations=recommendations,
        assumptions_used=assumptions_used or {},
        model_versions=model_versions or {},
    )
    db.add(log)
    await db.flush()
    return log


async def get_recent_logs(
    db: AsyncSession,
    port_code: str,
    limit: int = 50,
) -> List[BaosRecommendationLog]:
    """Get recent recommendation logs for a port."""
    result = await db.execute(
        select(BaosRecommendationLog)
        .join(BaosPort, BaosRecommendationLog.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
        .order_by(BaosRecommendationLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
