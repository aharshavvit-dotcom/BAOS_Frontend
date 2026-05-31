"""Recommendation API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.db.session import get_db
from backend.handlers.recommendations_handler import (
    generate_recommendation_handler,
    list_recommendations_handler,
    update_recommendation_handler,
)
from backend.schemas.recommendations import (
    RecommendationListResponse,
    RecommendationRequest,
    RecommendationResponse,
    UpdateRecommendationResponse,
    UpdateRecommendationRequest,
)

legacy_router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])
router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])


@legacy_router.post("/get-recommendation", response_model=RecommendationResponse)
@router.post("/get-recommendation", response_model=RecommendationResponse)
async def get_recommendation(
    req: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Generate berth recommendations for a vessel."""
    return await generate_recommendation_handler(db, req)


@legacy_router.get("", response_model=RecommendationListResponse)
@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    port_code: str = Query("INMAA"),
    rec_status: str = Query("all", alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """List recommendations with filtering and pagination."""
    # FIX (Phase 4): Recommendation history used limit/offset -> expose page/page_size capped at 100.
    return await list_recommendations_handler(db, port_code, rec_status, page, page_size)


@legacy_router.patch("/{recommendation_id}", response_model=UpdateRecommendationResponse)
@router.patch("/{recommendation_id}", response_model=UpdateRecommendationResponse)
async def update_recommendation(
    recommendation_id: str,
    req: UpdateRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Accept or reject a recommendation."""
    return await update_recommendation_handler(db, recommendation_id, req)
