"""Assumption request handlers."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.assumption_repository import (
    count_assumptions,
    get_assumptions,
    update_assumption,
)
from backend.schemas.assumptions import (
    AssumptionListResponse,
    AssumptionOut,
    PatchAssumptionRequest,
    PatchAssumptionResponse,
)


def _serialize_assumption(assumption) -> dict:
    return {
        "assumption_id": str(assumption.assumption_id),
        "port_id": str(assumption.port_id),
        "key": assumption.assumption_key,
        "value": assumption.assumption_value,
        "unit": assumption.unit,
        "source": assumption.source_quality,
        "confidence_multiplier": assumption.confidence_multiplier,
        "description": assumption.description,
        "used_in_decision": assumption.used_in_decision,
        "is_active": assumption.is_active,
    }


async def list_assumptions_handler(db: AsyncSession, port_code: str) -> list[dict]:
    """Return all assumptions for a port."""
    assumptions = await get_assumptions(db, port_code, active_only=False)
    return [_serialize_assumption(assumption) for assumption in assumptions]


async def list_assumptions_page_handler(
    db: AsyncSession,
    port_code: str,
    page: int,
    page_size: int,
) -> AssumptionListResponse:
    """Return paginated assumptions for a port."""
    # FIX (Phase 4): Assumptions returned a raw list -> standardize the paginated response.
    assumptions = await get_assumptions(
        db,
        port_code,
        active_only=False,
        page=page,
        page_size=page_size,
    )
    total = await count_assumptions(db, port_code, active_only=False)
    items = [AssumptionOut(**_serialize_assumption(assumption)) for assumption in assumptions]
    return AssumptionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )


async def patch_assumption_handler(
    db: AsyncSession,
    assumption_id: UUID,
    req: PatchAssumptionRequest,
) -> PatchAssumptionResponse:
    """Update an assumption and shape the API response."""
    updated = await update_assumption(
        db=db,
        assumption_id=assumption_id,
        value=req.value,
        is_active=req.is_active,
        description=req.description,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assumption {assumption_id} not found",
        )
    # FIX (Phase 4): Patch endpoint used response_model=dict -> return a typed patch response.
    return PatchAssumptionResponse(
        assumption_id=str(updated.assumption_id),
        key=updated.assumption_key,
        value=updated.assumption_value,
        is_active=updated.is_active,
        message="Assumption updated successfully",
    )
