"""
Dashboard API routes — KPIs, charts, recommendations overview.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from database.connection import get_db
from database.models import User
from schemas.dashboard import (
    ChartsResponse,
    DashboardRecommendationsResponse,
    KPIResponse,
)
from services.dashboard_service import (
    get_charts,
    get_dashboard_recommendations,
    get_kpis,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/kpis", response_model=KPIResponse)
async def kpis(
    port_code: str = Query("INMAA"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current KPI values for the dashboard."""
    return await get_kpis(db, port_code)


@router.get("/charts", response_model=ChartsResponse)
async def charts(
    port_code: str = Query("INMAA"),
    time_range: str = Query("30d"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chart data for the dashboard (monthly, utilization, vessels, costs)."""
    return await get_charts(db, port_code, time_range)


@router.get("/recommendations", response_model=DashboardRecommendationsResponse)
async def recommendations(
    port_code: str = Query("INMAA"),
    status: str = Query("all"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent recommendations for the dashboard overview."""
    return await get_dashboard_recommendations(db, port_code, status)
