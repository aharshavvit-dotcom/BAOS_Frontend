"""Dashboard request handlers."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.dashboard import (
    ChartsResponse,
    DashboardRecommendationsResponse,
    KPIResponse,
)
from backend.services.analytics_service import get_chart_analytics, get_kpi_analytics
from backend.services.dashboard_service import get_dashboard_recommendations


async def get_kpis_handler(db: AsyncSession, port_code: str) -> KPIResponse:
    """Return dashboard KPI data."""
    return await get_kpi_analytics(db, port_code)


async def get_charts_handler(
    db: AsyncSession,
    port_code: str,
    time_range: str,
) -> ChartsResponse:
    """Return dashboard chart data."""
    return await get_chart_analytics(db, port_code, time_range)


async def get_dashboard_recommendations_handler(
    db: AsyncSession,
    port_code: str,
    status: str,
) -> DashboardRecommendationsResponse:
    """Return dashboard recommendation data."""
    return await get_dashboard_recommendations(db, port_code, status)
