"""Analytics service facade for dashboard-oriented read models."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.dashboard import ChartsResponse, KPIResponse
from backend.services.dashboard_service import get_charts, get_kpis


async def get_kpi_analytics(db: AsyncSession, port_code: str) -> KPIResponse:
    """Return KPI analytics for a port."""
    return await get_kpis(db, port_code)


async def get_chart_analytics(
    db: AsyncSession,
    port_code: str,
    time_range: str,
) -> ChartsResponse:
    """Return chart analytics for a port."""
    return await get_charts(db, port_code, time_range)
