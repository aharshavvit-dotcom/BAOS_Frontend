"""
Berth Repository — CRUD for baos.berth and baos.berth_capability.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models.baos_models import BaosBerth, BaosBerthCapability, BaosPort


async def list_berths(
    db: AsyncSession,
    port_code: str,
    active_only: bool = True,
    page: int | None = None,
    page_size: int | None = None,
) -> List[BaosBerth]:
    """Return all berths for a port, with capabilities eager-loaded."""
    q = (
        select(BaosBerth)
        .join(BaosPort, BaosBerth.port_id == BaosPort.port_id)
        .options(selectinload(BaosBerth.capabilities), selectinload(BaosBerth.port))
        .where(BaosPort.port_code == port_code)
    )
    if active_only:
        q = q.where(BaosBerth.is_active == True)  # noqa: E712
    q = q.order_by(BaosBerth.berth_code)
    if page is not None and page_size is not None:
        # FIX (Phase 4): List endpoints loaded every berth -> apply offset/limit in the repository.
        q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def count_berths(
    db: AsyncSession,
    port_code: str,
    active_only: bool = True,
) -> int:
    """Return the berth count for a port."""
    q = (
        select(func.count(BaosBerth.berth_id))
        .join(BaosPort, BaosBerth.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
    )
    if active_only:
        q = q.where(BaosBerth.is_active == True)  # noqa: E712
    result = await db.execute(q)
    return int(result.scalar() or 0)


async def get_berth_by_code(
    db: AsyncSession, port_code: str, berth_code: str
) -> Optional[BaosBerth]:
    """Fetch a single berth by port_code + berth_code."""
    result = await db.execute(
        select(BaosBerth)
        .join(BaosPort, BaosBerth.port_id == BaosPort.port_id)
        .options(selectinload(BaosBerth.capabilities))
        .where(BaosPort.port_code == port_code, BaosBerth.berth_code == berth_code)
    )
    return result.scalar_one_or_none()


async def get_berth_capabilities(
    db: AsyncSession, port_code: str
) -> List[BaosBerthCapability]:
    """Return all berth capabilities for a port."""
    result = await db.execute(
        select(BaosBerthCapability)
        .join(BaosBerth, BaosBerthCapability.berth_id == BaosBerth.berth_id)
        .join(BaosPort, BaosBerth.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
    )
    return list(result.scalars().all())


async def berths_to_legacy_config(
    db: AsyncSession, port_code: str
) -> Dict:
    """
    Build a legacy-compatible port config dict from DB data.
    This replaces the old load_port_config() from JSON files.
    """
    from backend.db.repositories.port_repository import get_port_by_code

    port = await get_port_by_code(db, port_code)
    if not port:
        return {}

    berths = await list_berths(db, port_code)

    berth_list = []
    for b in berths:
        # Collect allowed vessel types from capabilities
        vessel_types = sorted(set(
            c.vessel_type for c in (b.capabilities or [])
            if c.vessel_type
        ))
        cargo_types = sorted(set(
            c.cargo_type for c in (b.capabilities or [])
            if c.cargo_type
        ))

        berth_list.append({
            "berth_code": b.berth_code,
            "berth_name": b.berth_name or b.berth_code,
            "terminal_code": b.terminal_name or "",
            "terminal_name": b.terminal_name or "",
            "port_code": port.port_code,
            "port_name": port.port_name,
            "max_loa_m": b.max_loa_m or 400.0,
            "max_beam_m": b.max_beam_m or 60.0,
            "max_draft_m": b.max_draft_m or 15.0,
            "depth_m": b.depth_m or 16.0,
            "allowed_vessel_types": vessel_types,
            "allowed_cargo_types": cargo_types,
            "equipment": sorted(set(
                c.equipment_type for c in (b.capabilities or [])
                if c.equipment_type
            )),
            "allow_24x7": True,
            "data_quality_level": b.data_quality_level or "SPEC",
        })

    return {
        "port_name": port.port_name,
        "port_code": port.port_code,
        "num_berths": len(berth_list),
        "berths": berth_list,
    }
