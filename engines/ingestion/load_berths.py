"""
Load Berths — Ingests Berth_configurations.xlsx into baos.berth.

Flow: Excel → stg_berth_config_raw → baos.berth
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Dict

import pandas as pd
from sqlalchemy.orm import Session

from engines.ingestion.excel_loader import compute_row_hash
from engines.ingestion.transformers import safe_float

logger = logging.getLogger(__name__)


def load_berths_from_excel(
    db: Session,
    file_path: str | Path,
    port_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> Dict[str, uuid.UUID]:
    """
    Ingest Berth_configurations.xlsx into staging then canonical tables.

    The Excel has a property-value format:
      Each row = one property for one berth.
      Columns: berthCode, berthName, terminalCode, terminalName,
               portCode, portName, propertyName, propertyValue, ...

    Returns:
        Dict[berth_code → berth_id] for downstream use.
    """
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    logger.info(f"Read {len(df)} property rows from {Path(file_path).name}")

    file_name = Path(file_path).name
    inserted = 0
    updated = 0

    # ── Stage 1: Load raw rows into staging ──────────────────
    from backend.db.models.baos_models import StgBerthConfigRaw
    for idx, row in df.iterrows():
        raw = row.to_dict()
        # Convert NaN/NaT to None for JSON
        clean_raw = {k: (None if pd.isna(v) else v) for k, v in raw.items()}
        for k, v in clean_raw.items():
            if isinstance(v, pd.Timestamp):
                clean_raw[k] = v.isoformat()
        stg = StgBerthConfigRaw(
            raw_payload=clean_raw,
            source_file_name=file_name,
            source_row_number=int(idx) + 2,  # Excel row (1-indexed + header)
            source_batch_id=batch_id,
            source_hash=compute_row_hash(clean_raw),
        )
        db.add(stg)

    db.flush()
    logger.info(f"Staged {len(df)} raw berth config rows")

    # ── Stage 2: Transform and upsert into canonical ─────────
    from backend.db.models.baos_models import BaosBerth

    # Group by berth code
    berth_map: Dict[str, uuid.UUID] = {}

    for bc, group in df.groupby("berthCode", dropna=False):
        bc_str = str(int(bc)) if pd.notna(bc) else str(bc)
        first = group.iloc[0]

        berth_name = str(first.get("berthName", "")) if pd.notna(first.get("berthName")) else bc_str
        terminal_name = str(first.get("terminalName", "")) if pd.notna(first.get("terminalName")) else ""

        # Parse properties
        props = {}
        for _, row in group.iterrows():
            pname = str(row.get("propertyName", "")).strip()
            pval = row.get("propertyValue")
            if pname:
                props[pname] = pval

        max_loa = safe_float(props.get("Max Length Overall (LOA)"))
        max_beam = safe_float(props.get("Max Beam (Width)"))
        max_draft = safe_float(props.get("Max Draft"))
        depth = safe_float(props.get("Max Depth"))

        # Handle "No Restrictions" → large default
        if max_loa is None and _is_no_restriction(props.get("Max Length Overall (LOA)")):
            max_loa = 999.0
        if max_beam is None and _is_no_restriction(props.get("Max Beam (Width)")):
            max_beam = 999.0
        if max_draft is None and _is_no_restriction(props.get("Max Draft")):
            max_draft = 30.0
        if depth is None and _is_no_restriction(props.get("Max Depth")):
            depth = 30.0

        # Check if berth already exists (upsert)
        existing = db.query(BaosBerth).filter(
            BaosBerth.port_id == port_id,
            BaosBerth.berth_code == bc_str,
        ).first()

        if existing:
            existing.berth_name = berth_name
            existing.terminal_name = terminal_name
            existing.max_loa_m = max_loa
            existing.max_beam_m = max_beam
            existing.max_draft_m = max_draft
            existing.depth_m = depth
            existing.source_batch_id = batch_id
            existing.data_quality_level = "SPEC"
            berth_map[bc_str] = existing.berth_id
            updated += 1
        else:
            berth_id = uuid.uuid4()
            berth = BaosBerth(
                berth_id=berth_id,
                port_id=port_id,
                berth_code=bc_str,
                berth_name=berth_name,
                terminal_name=terminal_name,
                max_loa_m=max_loa,
                max_beam_m=max_beam,
                max_draft_m=max_draft,
                depth_m=depth,
                source_batch_id=batch_id,
                data_quality_level="SPEC",
            )
            db.add(berth)
            berth_map[bc_str] = berth_id
            inserted += 1

    db.flush()
    logger.info(f"Berths: {inserted} inserted, {updated} updated")
    return berth_map


def _is_no_restriction(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    return str(val).strip().lower() == "no restrictions"
