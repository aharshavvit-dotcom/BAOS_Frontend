"""
Port Config Service — loads port configurations from the database.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.assumption_repository import get_assumptions_as_dict
from backend.db.repositories.berth_repository import berths_to_legacy_config
from backend.db.repositories.port_call_repository import get_historical_service_medians
from backend.db.repositories.port_repository import get_port_by_code

logger = logging.getLogger(__name__)

async def load_port_config_from_db(db: AsyncSession, port_code: str) -> Dict[str, Any]:
    """
    Build a full port config dictionary matching the format of legacy port_config.json files.
    """
    logger.info(f"Loading port config from DB for port: {port_code}")
    
    # 1. Get berths and port details using berth_repository helper
    config = await berths_to_legacy_config(db, port_code)
    if not config:
        logger.warning(f"No port configuration found in DB for port: {port_code}")
        return {}
        
    # 2. Get service time stats
    medians = await get_historical_service_medians(db, port_code)
    
    # Format service time stats matching the legacy json format
    service_time_stats = []
    for m in medians:
        service_time_stats.append({
            "port_code": port_code,
            "berth_code": m["berth_code"],
            "vessel_type": m["vessel_type"],
            "count": m["count"],
            "service_hours_median": m["avg_hours"],
            "service_hours_mean": m["avg_hours"],
        })
    config["service_time_stats"] = service_time_stats
    
    # 3. Get assumptions
    assumptions = await get_assumptions_as_dict(db, port_code)
    config["assumptions"] = assumptions
    
    # Add scheduling defaults
    config["planning_start"] = "2026-02-24T00:00:00"  # Default fallback planning start timestamp
    
    return config
