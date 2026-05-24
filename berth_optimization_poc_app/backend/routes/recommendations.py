"""
Recommendation API routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from database.connection import get_db
from database.models import Recommendation, User
from schemas.recommendations import (
    RecommendationItem,
    RecommendationListResponse,
    RecommendationRequest,
    RecommendationResponse,
    UpdateRecommendationRequest,
)
from services.recommendation_service import generate_recommendation

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.post("/get-recommendation", response_model=RecommendationResponse)
async def get_recommendation(
    req: RecommendationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate berth recommendations for a vessel."""
    return await generate_recommendation(
        db=db,
        vessel_name=req.vessel_name,
        vessel_type=req.vessel_type,
        loa_m=req.loa_m,
        beam_m=req.beam_m,
        draft_m=req.draft_m,
        dwt=req.dwt,
        cargo_type=req.cargo_type,
        cargo_tons=req.cargo_tons,
        port_code=req.port_code,
        eta=req.eta,
    )


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    port_code: str = Query("INMAA"),
    rec_status: str = Query("all", alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recommendations with filtering and pagination."""
    query = select(Recommendation).where(Recommendation.port_code == port_code)

    if rec_status != "all":
        query = query.where(Recommendation.status == rec_status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    query = query.order_by(Recommendation.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    recs = result.scalars().all()

    items = []
    for r in recs:
        vessel_data = r.vessel_data_json or {}
        items.append(RecommendationItem(
            id=str(r.id),
            vessel_name=vessel_data.get("vessel_name", "Unknown"),
            vessel_type=vessel_data.get("vessel_type", ""),
            berth_code=r.berth_code,
            berth_name=r.berth_name,
            confidence=r.confidence_score,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))

    return RecommendationListResponse(
        recommendations=items,
        total=total,
        page=(offset // limit) + 1,
        per_page=limit,
    )


@router.patch("/{recommendation_id}")
async def update_recommendation(
    recommendation_id: str,
    req: UpdateRecommendationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject a recommendation."""
    from uuid import UUID

    try:
        rec_uuid = UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation ID")

    result = await db.execute(
        select(Recommendation).where(Recommendation.id == rec_uuid)
    )
    rec = result.scalar_one_or_none()

    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = req.status
    await db.flush()

    return {
        "id": str(rec.id),
        "status": rec.status,
        "message": f"Recommendation {req.status} successfully",
    }
