"""Port management API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.db.session import get_db
from backend.handlers.ports_handler import (
    get_port_config_handler,
    get_port_status_handler,
    list_ports_handler,
)
from backend.schemas.ports import PortConfigOut, PortListResponse, PortStatusOut

router = APIRouter(prefix="/api/v1/ports", tags=["Ports"])


@router.get("", response_model=PortListResponse)
async def get_ports_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """List all available ports with training status."""
    # FIX (Phase 4): Port list used List[dict] -> typed paginated response model.
    return await list_ports_handler(db, page, page_size)


@router.get("/{port_code}/status", response_model=PortStatusOut)
async def get_port_status_details(
    port_code: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get detailed status for a specific port."""
    return await get_port_status_handler(db, port_code)


@router.get("/{port_code}/config", response_model=PortConfigOut)
async def get_port_config_details(
    port_code: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Get full port configuration including berth inventory."""
    return await get_port_config_handler(db, port_code)
