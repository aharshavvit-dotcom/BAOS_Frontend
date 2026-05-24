"""
Pydantic schemas for recommendation endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────────────

class RecommendationRequest(BaseModel):
    vessel_name: str = Field(..., min_length=1)
    vessel_type: str = ""
    loa_m: float = Field(0.0, ge=0)
    beam_m: float = Field(0.0, ge=0)
    draft_m: float = Field(0.0, ge=0)
    dwt: float = Field(0.0, ge=0)
    cargo_type: str = ""
    cargo_tons: float = Field(0.0, ge=0)
    eta: Optional[str] = None  # ISO datetime string
    port_code: str = "INMAA"


class UpdateRecommendationRequest(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected)$")


# ── Response ─────────────────────────────────────────────────────────────────

class BerthRecommendation(BaseModel):
    berth_code: str
    berth_name: str
    confidence: float
    technical_score: float = 0.0
    commercial_score: float = 0.0
    reasoning: Dict[str, Any] = {}
    expected_turnaround_hours: Optional[float] = None


class RecommendationResponse(BaseModel):
    recommendation_id: str
    recommendations: List[BerthRecommendation]
    vessel_name: str
    port_code: str


class RecommendationItem(BaseModel):
    id: str
    vessel_name: str
    vessel_type: str
    berth_code: str
    berth_name: str
    confidence: float
    status: str
    created_at: str


class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationItem]
    total: int
    page: int = 1
    per_page: int = 20
