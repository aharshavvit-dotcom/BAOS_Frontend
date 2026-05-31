"""
Pydantic schemas for recommendation endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import PaginatedResponse

# FIX (Phase 4): Recommendation history and updates needed typed response models.


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

    model_config = ConfigDict(from_attributes=True)


class UpdateRecommendationRequest(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected)$")

    model_config = ConfigDict(from_attributes=True)


# ── Response ─────────────────────────────────────────────────────────────────

class BerthRecommendation(BaseModel):
    berth_code: str
    berth_name: str
    confidence: float
    technical_score: float = 0.0
    commercial_score: float = 0.0
    reasoning: Dict[str, Any] = Field(default_factory=dict)
    expected_turnaround_hours: Optional[float] = None
    expected_wait_hours: Optional[float] = 0.0
    expected_service_hours: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    recommendation_id: str
    recommendations: List[BerthRecommendation]
    vessel_name: str
    port_code: str

    model_config = ConfigDict(from_attributes=True)


class RecommendationItem(BaseModel):
    id: str
    vessel_name: str
    vessel_type: str
    berth_code: str
    berth_name: str
    confidence: float
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class RecommendationListResponse(PaginatedResponse[RecommendationItem]):
    model_config = ConfigDict(from_attributes=True)


class UpdateRecommendationResponse(BaseModel):
    id: str
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)
