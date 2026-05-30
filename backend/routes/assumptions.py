"""
Assumptions API routes.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.assumption_repository import get_assumptions, update_assumption
from backend.db.session import get_db

router = APIRouter(prefix="/api/v1/assumptions", tags=["Assumptions"])


class PatchAssumptionRequest(BaseModel):
    value: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


@router.get("", response_model=List[dict])
async def list_port_assumptions(
    port_code: str = Query("INMAA"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all operational assumptions for a port."""
    assumptions = await get_assumptions(db, port_code, active_only=False)
    results = []
    for a in assumptions:
        results.append({
            "assumption_id": str(a.assumption_id),
            "port_id": str(a.port_id),
            "key": a.assumption_key,
            "value": a.assumption_value,
            "unit": a.unit,
            "source": a.source_quality,
            "confidence_multiplier": a.confidence_multiplier,
            "description": a.description,
            "used_in_decision": a.used_in_decision,
            "is_active": a.is_active,
        })
    return results


@router.patch("/{assumption_id}", response_model=dict)
async def patch_port_assumption(
    assumption_id: UUID,
    req: PatchAssumptionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update value or active status of a specific assumption."""
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
    return {
        "assumption_id": str(updated.assumption_id),
        "key": updated.assumption_key,
        "value": updated.assumption_value,
        "is_active": updated.is_active,
        "message": "Assumption updated successfully",
    }
