"""Berth API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.db.repositories.berth_repository import count_berths, list_berths as list_berths_repo
from backend.db.session import get_db
from backend.schemas.berths import BerthListResponse, BerthOut

router = APIRouter(prefix="/api/v1/berths", tags=["Berths"])


def _serialize_berth(berth, port_code: str) -> BerthOut:
    vessel_types = sorted(set(
        capability.vessel_type for capability in (berth.capabilities or [])
        if capability.vessel_type
    ))
    cargo_types = sorted(set(
        capability.cargo_type for capability in (berth.capabilities or [])
        if capability.cargo_type
    ))
    equipment = sorted(set(
        capability.equipment_type for capability in (berth.capabilities or [])
        if capability.equipment_type
    ))
    return BerthOut(
        berth_code=berth.berth_code,
        berth_name=berth.berth_name or berth.berth_code,
        terminal_code=berth.terminal_name or "",
        terminal_name=berth.terminal_name or "",
        port_code=port_code,
        port_name=berth.port.port_name if berth.port else port_code,
        max_loa_m=berth.max_loa_m or 400.0,
        max_beam_m=berth.max_beam_m or 60.0,
        max_draft_m=berth.max_draft_m or 15.0,
        depth_m=berth.depth_m or 16.0,
        allowed_vessel_types=vessel_types,
        allowed_cargo_types=cargo_types,
        equipment=equipment,
        allow_24x7=True,
        data_quality_level=berth.data_quality_level or "SPEC",
    )


@router.get("", response_model=BerthListResponse)
async def list_berths(
    port_code: str = Query("INMAA"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """List berths for a port."""
    normalized_port_code = port_code.strip().upper()
    # FIX (Phase 4): Berth list returned a raw unpaginated list -> typed paginated API contract.
    berths = await list_berths_repo(db, normalized_port_code, page=page, page_size=page_size)
    total = await count_berths(db, normalized_port_code)
    return BerthListResponse(
        items=[_serialize_berth(berth, normalized_port_code) for berth in berths],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 0,
    )
