"""Pydantic schemas for berth endpoints."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import PaginatedResponse

# FIX (Phase 4): Berth endpoints exposed list[dict] -> define clean public response schemas.


class BerthOut(BaseModel):
    berth_code: str
    berth_name: str
    terminal_code: str = ""
    terminal_name: str = ""
    port_code: str
    port_name: str
    max_loa_m: float
    max_beam_m: float
    max_draft_m: float
    depth_m: float
    allowed_vessel_types: list[str] = Field(default_factory=list)
    allowed_cargo_types: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    allow_24x7: bool = True
    data_quality_level: str = "SPEC"

    model_config = ConfigDict(from_attributes=True)


class BerthListResponse(PaginatedResponse[BerthOut]):
    model_config = ConfigDict(from_attributes=True)
