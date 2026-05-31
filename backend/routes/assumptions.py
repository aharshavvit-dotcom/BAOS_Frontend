"""Assumptions API routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.db.session import get_db
from backend.handlers.assumptions_handler import (
    list_assumptions_page_handler,
    patch_assumption_handler,
)
from backend.schemas.assumptions import (
    AssumptionListResponse,
    PatchAssumptionRequest,
    PatchAssumptionResponse,
)

router = APIRouter(prefix="/api/v1/assumptions", tags=["Assumptions"])


@router.get("", response_model=AssumptionListResponse)
async def list_port_assumptions(
    port_code: str = Query("INMAA"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Retrieve all operational assumptions for a port."""
    return await list_assumptions_page_handler(db, port_code, page, page_size)


@router.patch("/{assumption_id}", response_model=PatchAssumptionResponse)
async def patch_port_assumption(
    assumption_id: UUID,
    req: PatchAssumptionRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Update value or active status of a specific assumption."""
    return await patch_assumption_handler(db, assumption_id, req)
