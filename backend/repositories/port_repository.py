"""
Port Repository — CRUD for baos.port table.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.baos_models import BaosPort


async def list_ports(db: AsyncSession, active_only: bool = True) -> List[BaosPort]:
    """Return all ports, optionally filtered to active only."""
    q = select(BaosPort)
    if active_only:
        q = q.where(BaosPort.is_active == True)  # noqa: E712
    q = q.order_by(BaosPort.port_name)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_port_by_code(db: AsyncSession, port_code: str) -> Optional[BaosPort]:
    """Fetch a single port by its code (e.g. 'INMAA')."""
    result = await db.execute(
        select(BaosPort).where(BaosPort.port_code == port_code)
    )
    return result.scalar_one_or_none()


async def get_port_by_id(db: AsyncSession, port_id: UUID) -> Optional[BaosPort]:
    """Fetch a single port by UUID."""
    result = await db.execute(
        select(BaosPort).where(BaosPort.port_id == port_id)
    )
    return result.scalar_one_or_none()


async def upsert_port(
    db: AsyncSession,
    port_code: str,
    port_name: str,
    country: str = "India",
    timezone: str = "Asia/Kolkata",
) -> BaosPort:
    """Create or update a port record."""
    existing = await get_port_by_code(db, port_code)
    if existing:
        existing.port_name = port_name
        existing.country = country
        existing.timezone = timezone
        await db.flush()
        return existing
    port = BaosPort(
        port_code=port_code,
        port_name=port_name,
        country=country,
        timezone=timezone,
    )
    db.add(port)
    await db.flush()
    return port


async def port_exists(db: AsyncSession, port_code: str) -> bool:
    """Check if a port exists by code."""
    p = await get_port_by_code(db, port_code)
    return p is not None
