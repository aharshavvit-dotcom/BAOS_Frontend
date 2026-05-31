"""Recommendation request handlers."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.recommendation_repository import (
    list_app_recommendations,
    update_app_recommendation_status,
)
from backend.schemas.recommendations import (
    RecommendationItem,
    RecommendationListResponse,
    RecommendationRequest,
    RecommendationResponse,
    UpdateRecommendationResponse,
    UpdateRecommendationRequest,
)
from backend.services.recommendation_service import generate_recommendation


async def generate_recommendation_handler(
    db: AsyncSession,
    req: RecommendationRequest,
) -> RecommendationResponse:
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


async def list_recommendations_handler(
    db: AsyncSession,
    port_code: str,
    rec_status: str,
    page: int,
    page_size: int,
) -> RecommendationListResponse:
    """Return paginated recommendations."""
    recommendations, total = await list_app_recommendations(
        db,
        port_code=port_code,
        rec_status=rec_status,
        page=page,
        page_size=page_size,
    )

    items = []
    for recommendation in recommendations:
        vessel_data = recommendation.vessel_data_json or {}
        items.append(RecommendationItem(
            id=str(recommendation.id),
            vessel_name=vessel_data.get("vessel_name", "Unknown"),
            vessel_type=vessel_data.get("vessel_type", ""),
            berth_code=recommendation.berth_code,
            berth_name=recommendation.berth_name,
            confidence=recommendation.confidence_score,
            status=recommendation.status,
            created_at=recommendation.created_at.isoformat() if recommendation.created_at else "",
        ))

    # FIX (Phase 4): Recommendation history used a custom wrapper -> return items/page/page_size.
    return RecommendationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


async def update_recommendation_handler(
    db: AsyncSession,
    recommendation_id: str,
    req: UpdateRecommendationRequest,
) -> UpdateRecommendationResponse:
    """Accept or reject a recommendation."""
    try:
        rec_uuid = UUID(recommendation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid recommendation ID") from exc

    recommendation = await update_app_recommendation_status(db, rec_uuid, req.status)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # FIX (Phase 4): Update endpoint had no response_model -> return a typed status payload.
    return UpdateRecommendationResponse(
        id=str(recommendation.id),
        status=recommendation.status,
        message=f"Recommendation {req.status} successfully",
    )
