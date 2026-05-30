"""
Training Data Service — fetches training-eligible port calls from the DB.
"""
from __future__ import annotations

import logging
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.port_call_repository import get_training_rows

logger = logging.getLogger(__name__)

async def load_history_from_db(db: AsyncSession, port_code: str) -> pd.DataFrame:
    """
    Fetch all training-eligible port calls from the database and return as a Pandas DataFrame.
    Maps database column names back to legacy CSV names expected by the ML engine.
    """
    logger.info(f"Loading historical training data from DB for port: {port_code}")
    port_calls = await get_training_rows(db, port_code)
    
    if not port_calls:
        logger.warning(f"No training-eligible port calls found in DB for port: {port_code}")
        return pd.DataFrame()
        
    rows = []
    for pc in port_calls:
        rows.append({
            "port_call_id": str(pc.port_call_id),
            "portcode": port_code,
            "berthcode": pc.berth_code_raw,
            "vesseltype": pc.vessel_type,
            "name": pc.vessel_name,
            "imo": pc.vessel_imo,
            "cargo_type": pc.cargo_type,
            "loa": pc.loa_m,
            "beam": pc.beam_m,
            "adraft": pc.arrival_draft_m,
            "ddraught": pc.departure_draft_m,
            "dwt": pc.dwt,
            "cargo_tons": pc.cargo_tons,
            "eosp": pc.eosp_ts.isoformat() if pc.eosp_ts else None,
            "pob": pc.pob_ts.isoformat() if pc.pob_ts else None,
            "all_fast": pc.all_fast_ts.isoformat() if pc.all_fast_ts else None,
            "last_line": pc.last_line_ts.isoformat() if pc.last_line_ts else None,
            "cosp": pc.cosp_ts.isoformat() if pc.cosp_ts else None,
            "pilot_wait_h": pc.pilot_wait_hours,
            "pilot_to_berth_h": pc.pilot_to_berth_hours,
            "berth_occupancy_h": pc.berth_occupancy_hours,
            "unberth_outbound_h": pc.unberth_outbound_hours,
            "total_port_stay_h": pc.total_port_stay_hours,
            "is_valid_for_training": pc.is_valid_for_training,
        })
        
    df = pd.DataFrame(rows)
    logger.info(f"Loaded {len(df)} historical port calls from DB")
    return df
