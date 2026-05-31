"""Allocation service facade for optimizer inputs and allocation workflows."""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.optimization_data_service import get_optimizer_inputs


async def get_allocation_inputs(db: AsyncSession, port_code: str) -> Dict[str, Any]:
    """Return optimizer-ready allocation inputs for a port."""
    return await get_optimizer_inputs(db, port_code)
