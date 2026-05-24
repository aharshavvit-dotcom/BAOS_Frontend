"""
Pydantic schemas for dashboard endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class KPIValue(BaseModel):
    label: str
    value: float | int | str
    change_pct: Optional[float] = None
    trend: Optional[str] = None  # "up" | "down" | "flat"
    icon: Optional[str] = None


class KPIResponse(BaseModel):
    vessels_count: int = 0
    revenue: float = 0.0
    cost: float = 0.0
    utilization_pct: float = 0.0
    sla_compliance_pct: float = 0.0
    avg_turnaround_hours: float = 0.0
    kpi_cards: List[KPIValue] = []


class ChartDataset(BaseModel):
    label: str
    data: List[float]
    backgroundColor: Optional[Any] = None
    borderColor: Optional[str] = None
    borderWidth: Optional[float] = None
    fill: Optional[bool] = None
    tension: Optional[float] = None
    borderRadius: Optional[int] = None
    borderSkipped: Optional[bool] = None
    borderDash: Optional[List[int]] = None
    pointRadius: Optional[float] = None
    pointBackgroundColor: Optional[str] = None
    pointBorderColor: Optional[str] = None
    pointBorderWidth: Optional[float] = None
    type: Optional[str] = None
    hoverOffset: Optional[int] = None
    cutout: Optional[str] = None


class ChartData(BaseModel):
    labels: List[str]
    datasets: List[ChartDataset]


class ChartsResponse(BaseModel):
    monthly_comparison: ChartData
    utilization_trend: ChartData
    vessel_distribution: ChartData
    cost_breakdown: ChartData


class DashboardRecommendation(BaseModel):
    id: str
    vessel_name: str
    vessel_type: str
    berth_name: str
    confidence: float
    status: str  # "pending" | "accepted" | "rejected"
    created_at: str


class DashboardRecommendationsResponse(BaseModel):
    recommendations: List[DashboardRecommendation]
    total: int
