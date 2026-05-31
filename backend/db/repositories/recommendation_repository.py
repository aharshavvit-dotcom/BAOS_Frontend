"""
Recommendation Repository — CRUD for baos.recommendation_log.
"""
from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.app_models import Recommendation
from backend.db.models.baos_models import BaosPort, BaosRecommendationLog


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


async def list_app_recommendations(
    db: AsyncSession,
    port_code: str,
    rec_status: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Recommendation], int]:
    """List app recommendations from the dashboard-facing table."""
    query = select(Recommendation).where(Recommendation.port_code == port_code)
    if rec_status != "all":
        query = query.where(Recommendation.status == rec_status)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # FIX (Phase 4): Recommendation history used limit/offset at the API edge -> repository owns paging.
    page_query = (
        query.order_by(Recommendation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(page_query)
    return list(result.scalars().all()), total


async def update_app_recommendation_status(
    db: AsyncSession,
    recommendation_id: UUID,
    rec_status: str,
) -> Recommendation | None:
    """Update an app recommendation status."""
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    )
    recommendation = result.scalar_one_or_none()
    if recommendation is None:
        return None

    recommendation.status = rec_status
    await db.flush()
    return recommendation
