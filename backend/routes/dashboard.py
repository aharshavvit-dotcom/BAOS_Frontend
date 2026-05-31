"""Dashboard API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.db.session import get_db
from backend.handlers.dashboard_handler import (
    get_charts_handler,
    get_dashboard_recommendations_handler,
    get_kpis_handler,
)
from backend.schemas.dashboard import (
    ChartsResponse,
    DashboardRecommendationsResponse,
    KPIResponse,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/kpis", response_model=KPIResponse)
async def kpis(
    port_code: str = Query("INMAA"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get current KPI values for the dashboard."""
    return await get_kpis_handler(db, port_code)


@router.get("/charts", response_model=ChartsResponse)
async def charts(
    port_code: str = Query("INMAA"),
    time_range: str = Query("30d"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get chart data for the dashboard."""
    return await get_charts_handler(db, port_code, time_range)


@router.get("/recommendations", response_model=DashboardRecommendationsResponse)
async def recommendations(
    port_code: str = Query("INMAA"),
    status: str = Query("all"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get recent recommendations for the dashboard overview."""
    return await get_dashboard_recommendations_handler(db, port_code, status)
