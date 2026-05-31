"""Pydantic schemas for system endpoints."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# FIX (Phase 4): System endpoints returned raw dicts -> define typed response schemas.


class RootResponse(BaseModel):
    name: str
    version: str
    docs: str
    health: str

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

    model_config = ConfigDict(from_attributes=True)
