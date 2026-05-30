"""
Assumption Repository — CRUD for baos.assumption_config.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.baos_models import BaosAssumptionConfig, BaosPort


async def get_assumptions(
    db: AsyncSession,
    port_code: str,
    active_only: bool = True,
) -> List[BaosAssumptionConfig]:
    """Return all assumptions for a port."""
    q = (
        select(BaosAssumptionConfig)
        .join(BaosPort, BaosAssumptionConfig.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
    )
    if active_only:
        q = q.where(BaosAssumptionConfig.is_active == True)  # noqa: E712
    q = q.order_by(BaosAssumptionConfig.assumption_key)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_assumption_value(
    db: AsyncSession,
    port_code: str,
    key: str,
    default: float = 0.0,
) -> float:
    """Get a single assumption value by key."""
    q = (
        select(BaosAssumptionConfig.assumption_value)
        .join(BaosPort, BaosAssumptionConfig.port_id == BaosPort.port_id)
        .where(
            BaosPort.port_code == port_code,
            BaosAssumptionConfig.assumption_key == key,
            BaosAssumptionConfig.is_active == True,  # noqa: E712
        )
    )
    result = await db.execute(q)
    val = result.scalar_one_or_none()
    return val if val is not None else default


async def get_assumptions_as_dict(
    db: AsyncSession,
    port_code: str,
) -> Dict[str, float]:
    """Return all assumptions as {key: value} dict."""
    assumptions = await get_assumptions(db, port_code)
    return {a.assumption_key: a.assumption_value for a in assumptions}


async def update_assumption(
    db: AsyncSession,
    assumption_id: UUID,
    value: Optional[float] = None,
    is_active: Optional[bool] = None,
    description: Optional[str] = None,
) -> Optional[BaosAssumptionConfig]:
    """Patch an assumption record."""
    result = await db.execute(
        select(BaosAssumptionConfig)
        .where(BaosAssumptionConfig.assumption_id == assumption_id)
    )
    assumption = result.scalar_one_or_none()
    if not assumption:
        return None

    if value is not None:
        assumption.assumption_value = value
    if is_active is not None:
        assumption.is_active = is_active
    if description is not None:
        assumption.description = description

    await db.flush()
    return assumption
