"""
Load Capabilities — Ingests Operational_Capability_of_Berth.xlsx into baos.berth_capability.

Flow: Excel → stg_berth_capability_raw → baos.berth_capability
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Dict

import pandas as pd
from sqlalchemy.orm import Session

from data_ingestion.excel_loader import compute_row_hash

logger = logging.getLogger(__name__)


def load_capabilities_from_excel(
    db: Session,
    file_path: str | Path,
    port_id: uuid.UUID,
    batch_id: uuid.UUID,
    berth_map: Dict[str, uuid.UUID],
) -> int:
    """
    Ingest Operational_Capability_of_Berth.xlsx into staging then canonical tables.

    Columns: berthCode, berthName, terminalName, terminalCode, terminalType,
             operation, commodity, commodityGroup, cargoCategory

    Returns:
        Number of capability rows inserted.
    """
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    logger.info(f"Read {len(df)} capability rows from {Path(file_path).name}")

    file_name = Path(file_path).name
    inserted = 0

    # ── Stage 1: Load raw rows into staging ──────────────────
    from database.baos_models import StgBerthCapabilityRaw
    for idx, row in df.iterrows():
        raw = row.to_dict()
        clean_raw = {k: (None if pd.isna(v) else v) for k, v in raw.items()}
        stg = StgBerthCapabilityRaw(
            raw_payload=clean_raw,
            source_file_name=file_name,
            source_row_number=int(idx) + 2,
            source_batch_id=batch_id,
            source_hash=compute_row_hash(clean_raw),
        )
        db.add(stg)

    db.flush()

    # ── Stage 2: Transform and insert into canonical ─────────
    from database.baos_models import BaosBerthCapability

    # Delete existing capabilities for this batch's berths to allow re-ingestion
    berth_ids = list(berth_map.values())
    if berth_ids:
        db.query(BaosBerthCapability).filter(
            BaosBerthCapability.berth_id.in_(berth_ids),
        ).delete(synchronize_session=False)
        db.flush()

    for _, row in df.iterrows():
        bc = row.get("berthCode")
        bc_str = str(int(bc)) if pd.notna(bc) else str(bc)
        berth_id = berth_map.get(bc_str)
        if not berth_id:
            logger.warning(f"Berth {bc_str} not found in berth_map — skipping capability row")
            continue

        operation = str(row.get("operation", "")).strip() if pd.notna(row.get("operation")) else None
        commodity = str(row.get("commodity", "")).strip() if pd.notna(row.get("commodity")) else None
        cargo_cat = str(row.get("cargoCategory", "")).strip() if pd.notna(row.get("cargoCategory")) else None

        cap = BaosBerthCapability(
            capability_id=uuid.uuid4(),
            berth_id=berth_id,
            vessel_type=operation,  # operation maps to vessel/cargo handling type
            cargo_type=commodity or cargo_cat,
            equipment_type=None,
            data_quality_level="SPEC",
            source_batch_id=batch_id,
        )
        db.add(cap)
        inserted += 1

    db.flush()
    logger.info(f"Capabilities: {inserted} inserted")
    return inserted
