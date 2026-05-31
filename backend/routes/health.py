"""System routes."""
from __future__ import annotations

from fastapi import APIRouter

from backend.handlers.system_handler import health_response, root_response
from backend.schemas.system import HealthResponse, RootResponse

router = APIRouter(tags=["System"])


@router.get("/", response_model=RootResponse)
async def root():
    """API welcome page."""
    return await root_response()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return await health_response()
