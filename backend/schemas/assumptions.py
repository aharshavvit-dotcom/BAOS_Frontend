"""Pydantic schemas for assumption endpoints."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from backend.schemas.common import PaginatedResponse

# FIX (Phase 4): Assumption endpoints exposed raw dict/list responses -> define typed schemas.


class PatchAssumptionRequest(BaseModel):
    value: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AssumptionOut(BaseModel):
    assumption_id: str
    key: str
    value: float
    unit: str | None = None
    source: str | None = None
    confidence_multiplier: float | None = None
    description: str | None = None
    used_in_decision: bool = True
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class AssumptionListResponse(PaginatedResponse[AssumptionOut]):
    model_config = ConfigDict(from_attributes=True)


class PatchAssumptionResponse(BaseModel):
    assumption_id: str
    key: str
    value: float
    is_active: bool
    message: str

    model_config = ConfigDict(from_attributes=True)
