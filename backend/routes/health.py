"""Health check routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.config import settings

router = APIRouter(tags=["System"])


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
