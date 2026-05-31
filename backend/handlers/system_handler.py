"""System endpoint handlers."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.config import settings
from backend.schemas.system import HealthResponse, RootResponse


async def root_response() -> RootResponse:
    """Return API metadata."""
    # FIX (Phase 4): System root had no response_model -> return a typed metadata payload.
    return RootResponse(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs="/docs",
        health="/health",
    )


async def health_response() -> HealthResponse:
    """Return health metadata."""
    # FIX (Phase 4): Health returned a raw dict -> return a typed health payload.
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
