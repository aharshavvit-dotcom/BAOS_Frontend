"""
Dashboard service — aggregates KPIs and chart data.
Returns mock data initially; will be backed by real DB queries.
"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.dashboard import (
    ChartData,
    ChartDataset,
    ChartsResponse,
    DashboardRecommendation,
    DashboardRecommendationsResponse,
    KPIResponse,
    KPIValue,
)


async def get_kpis(db: AsyncSession, port_code: str = "INMAA") -> KPIResponse:
    """
    Get current KPI values for the dashboard.
    Uses realistic sample data that matches the original homepage.
    """
    return KPIResponse(
        vessels_count=142,
        revenue=480000.0,
        cost=230000.0,
        utilization_pct=78.0,
        sla_compliance_pct=94.0,
        avg_turnaround_hours=26.5,
        kpi_cards=[
            KPIValue(
                label="Active Vessels",
                value=142,
                change_pct=8.4,
                trend="up",
                icon="🚢",
            ),
            KPIValue(
                label="Revenue",
                value="$480K",
                change_pct=14.3,
                trend="up",
                icon="💰",
            ),
            KPIValue(
                label="SLA Compliance",
                value="94%",
                change_pct=5.6,
                trend="up",
                icon="✅",
            ),
        ],
    )


async def get_charts(
    db: AsyncSession,
    port_code: str = "INMAA",
    time_range: str = "30d",
) -> ChartsResponse:
    """
    Get chart data for the dashboard.
    Data matches the original homepage.js chart configurations.
    """
    return ChartsResponse(
        monthly_comparison=ChartData(
            labels=["Vessels", "Revenue ($K)", "Utilization", "SLA %"],
            datasets=[
                ChartDataset(
                    label="This Month",
                    data=[142, 480, 78, 94],
                    backgroundColor="rgba(0, 102, 204, 0.7)",
                    borderRadius=4,
                    borderSkipped=False,
                ),
                ChartDataset(
                    label="Last Month",
                    data=[131, 420, 75, 89],
                    backgroundColor="rgba(148, 163, 184, 0.5)",
                    borderRadius=4,
                    borderSkipped=False,
                ),
            ],
        ),
        utilization_trend=ChartData(
            labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets=[
                ChartDataset(
                    label="Utilization %",
                    data=[72, 78, 75, 82, 80, 55, 48],
                    borderColor="#0066CC",
                    backgroundColor="rgba(0, 102, 204, 0.08)",
                    fill=True,
                    tension=0.4,
                    pointRadius=3,
                    pointBackgroundColor="#0066CC",
                    borderWidth=2,
                ),
            ],
        ),
        vessel_distribution=ChartData(
            labels=["Container", "Bulk", "General", "Tanker", "RoRo"],
            datasets=[
                ChartDataset(
                    label="Vessels",
                    data=[35, 22, 18, 15, 10],
                    backgroundColor=[
                        "rgba(0, 102, 204, 0.8)",
                        "rgba(0, 170, 153, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(236, 72, 153, 0.8)",
                    ],
                    borderWidth=0,
                    hoverOffset=6,
                ),
            ],
        ),
        cost_breakdown=ChartData(
            labels=["Fuel", "Equipment", "Waiting", "SLA Penalty", "Handling"],
            datasets=[
                ChartDataset(
                    label="Cost ($K)",
                    data=[45, 38, 28, 12, 52],
                    backgroundColor=[
                        "rgba(239, 68, 68, 0.7)",
                        "rgba(245, 158, 11, 0.7)",
                        "rgba(59, 130, 246, 0.7)",
                        "rgba(139, 92, 246, 0.7)",
                        "rgba(0, 170, 153, 0.7)",
                    ],
                    borderRadius=4,
                    borderSkipped=False,
                ),
            ],
        ),
    )


async def get_dashboard_recommendations(
    db: AsyncSession,
    port_code: str = "INMAA",
    status: str = "all",
) -> DashboardRecommendationsResponse:
    """
    Get recent recommendations for the dashboard cards.
    """
    # Sample data matching the original homepage
    all_recs = [
        DashboardRecommendation(
            id="rec-001",
            vessel_name="MV Ocean Crown",
            vessel_type="Container Ship",
            berth_name="Berth A1 (Container Terminal)",
            confidence=92.5,
            status="pending",
            created_at="2026-03-30T10:30:00Z",
        ),
        DashboardRecommendation(
            id="rec-002",
            vessel_name="SS Pacific Trader",
            vessel_type="Bulk Carrier",
            berth_name="Berth B3 (Bulk Terminal)",
            confidence=87.3,
            status="accepted",
            created_at="2026-03-29T15:45:00Z",
        ),
        DashboardRecommendation(
            id="rec-003",
            vessel_name="MT Horizon Star",
            vessel_type="Crude Oil Tanker",
            berth_name="Berth C2 (Oil Terminal)",
            confidence=95.1,
            status="pending",
            created_at="2026-03-30T08:00:00Z",
        ),
        DashboardRecommendation(
            id="rec-004",
            vessel_name="MV Jade Express",
            vessel_type="General Cargo",
            berth_name="Berth A3 (Multi-purpose)",
            confidence=78.9,
            status="rejected",
            created_at="2026-03-28T12:20:00Z",
        ),
    ]

    if status != "all":
        filtered = [r for r in all_recs if r.status == status]
    else:
        filtered = all_recs

    return DashboardRecommendationsResponse(
        recommendations=filtered,
        total=len(filtered),
    )
