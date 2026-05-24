"""
Optimization Data Service — builds optimizer inputs from DB repositories.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.berth_repository import list_berths
from repositories.port_repository import get_port_by_code
from repositories.assumption_repository import get_assumptions_as_dict
from optimization_engine.constraint_model import BerthInput, ResourceInput, SchedulerConfig

logger = logging.getLogger(__name__)

async def get_optimizer_inputs(db: AsyncSession, port_code: str) -> Dict[str, Any]:
    """
    Get all port-related inputs required by the optimization engine from the database.
    """
    logger.info(f"Building optimizer inputs from DB for port: {port_code}")
    
    # 1. Fetch berths from DB
    db_berths = await list_berths(db, port_code)
    berth_inputs = []
    for b in db_berths:
        # Collect allowed vessel types from capabilities
        vessel_types = sorted(set(
            c.vessel_type for c in (b.capabilities or [])
            if c.vessel_type
        ))
        
        berth_inputs.append(BerthInput(
            berth_code=b.berth_code,
            berth_name=b.berth_name or b.berth_code,
            max_loa_m=b.max_loa_m or 300.0,
            max_beam_m=b.max_beam_m or 50.0,
            max_draft_m=b.max_draft_m or 15.0,
            depth_m=b.depth_m or 15.0,
            allowed_vessel_types=vessel_types,
            allow_24x7=True,
        ))
        
    # 2. Build default resource capacities
    # In the database-first architecture, resource slots are defined.
    # For now, we return sensible default resource allocations.
    resources = [
        ResourceInput("pilot", capacity=2),
        ResourceInput("tug", capacity=3),
    ]
    
    # 3. Load assumptions to build scheduler configuration overrides
    assumptions = await get_assumptions_as_dict(db, port_code)
    
    return {
        "berths": berth_inputs,
        "resources": resources,
        "assumptions": assumptions,
    }
