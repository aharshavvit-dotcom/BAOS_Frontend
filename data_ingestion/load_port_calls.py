"""
Load Port Calls — Ingests port call log Excel/CSV into baos.port_call.

Flow: Excel/CSV → stg_port_call_raw → validate → baos.port_call
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from sqlalchemy.orm import Session

from data_ingestion.excel_loader import compute_row_hash
from data_ingestion.schema_mapping import normalize_columns
from data_ingestion.transformers import safe_float, safe_datetime, compute_derived_durations
from data_ingestion.validators import validate_port_call_row

logger = logging.getLogger(__name__)


def load_port_calls_from_file(
    db: Session,
    file_path: str | Path,
    port_id: uuid.UUID,
    batch_id: uuid.UUID,
    berth_map: Optional[Dict[str, uuid.UUID]] = None,
) -> Dict[str, int]:
    """
    Ingest a port call log (Excel or CSV) into staging then canonical tables.

    Returns:
        Dict with counts: total, inserted, updated, rejected, outlier.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
        file_type = "excel"
    elif ext == ".csv":
        df = pd.read_csv(path)
        file_type = "csv"
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    df.columns = df.columns.str.strip()
    logger.info(f"Read {len(df)} rows from {path.name}")

    file_name = path.name
    berth_map = berth_map or {}

    # Resolve column names
    col_map = normalize_columns(df.columns.tolist())

    # ── Stage 1: Load raw rows into staging ──────────────────
    from database.baos_models import StgPortCallRaw

    for idx, row in df.iterrows():
        raw = row.to_dict()
        clean_raw = {}
        for k, v in raw.items():
            if pd.isna(v):
                clean_raw[k] = None
            elif isinstance(v, pd.Timestamp):
                clean_raw[k] = v.isoformat()
            else:
                clean_raw[k] = v
        stg = StgPortCallRaw(
            raw_payload=clean_raw,
            source_file_name=file_name,
            source_row_number=int(idx) + 2,
            source_batch_id=batch_id,
            source_hash=compute_row_hash(clean_raw),
        )
        db.add(stg)

    db.flush()
    logger.info(f"Staged {len(df)} raw port call rows")

    # ── Stage 2: Transform and upsert into canonical ─────────
    from database.baos_models import BaosPortCall

    counts = {"total": len(df), "inserted": 0, "updated": 0, "rejected": 0, "outlier": 0}

    for idx, row in df.iterrows():
        try:
            # Map columns using aliases
            mapped = {}
            for canonical, original in col_map.items():
                mapped[canonical] = row.get(original)

            # Build record
            berth_code_raw = str(int(mapped.get("berth_code"))) if pd.notna(mapped.get("berth_code")) else None
            berth_id = berth_map.get(berth_code_raw) if berth_code_raw else None

            record = {
                "vessel_name": str(mapped.get("vessel_name", "")) if pd.notna(mapped.get("vessel_name")) else None,
                "vessel_imo": str(mapped.get("vessel_imo", "")) if pd.notna(mapped.get("vessel_imo")) else None,
                "vessel_type": str(mapped.get("vessel_type", "")) if pd.notna(mapped.get("vessel_type")) else None,
                "cargo_type": str(mapped.get("cargo_type", "")) if pd.notna(mapped.get("cargo_type")) else None,
                "berth_code_raw": berth_code_raw,
                "berth_id": berth_id,
                "loa_m": safe_float(mapped.get("loa_m")),
                "beam_m": safe_float(mapped.get("beam_m")),
                "arrival_draft_m": safe_float(mapped.get("arrival_draft_m")),
                "departure_draft_m": safe_float(mapped.get("departure_draft_m")),
                "dwt": safe_float(mapped.get("dwt")),
                "cargo_tons": safe_float(mapped.get("cargo_tons")),
                "eosp_ts": safe_datetime(mapped.get("eosp_ts")),
                "pob_ts": safe_datetime(mapped.get("pob_ts")),
                "all_fast_ts": safe_datetime(mapped.get("all_fast_ts")),
                "last_line_ts": safe_datetime(mapped.get("last_line_ts")),
                "cosp_ts": safe_datetime(mapped.get("cosp_ts")),
            }

            # Compute derived durations
            durations = compute_derived_durations(record)
            record.update(durations)

            # Validate
            validation = validate_port_call_row(record)
            record["is_valid_for_training"] = validation.is_valid_for_training
            record["validation_status"] = validation.status
            record["validation_notes"] = "; ".join(validation.notes) if validation.notes else None

            if validation.status == "OUTLIER":
                counts["outlier"] += 1

            # Compute source hash for deduplication
            hash_data = {
                "berth": berth_code_raw,
                "imo": record.get("vessel_imo"),
                "eosp": str(record.get("eosp_ts")),
                "cosp": str(record.get("cosp_ts")),
            }
            source_hash = compute_row_hash(hash_data)

            # Check for duplicate (upsert)
            existing = db.query(BaosPortCall).filter(
                BaosPortCall.port_id == port_id,
                BaosPortCall.source_hash == source_hash,
            ).first()

            if existing:
                # Update existing record
                for key, val in record.items():
                    if key not in ("berth_id",) or val is not None:
                        setattr(existing, key, val)
                existing.source_batch_id = batch_id
                existing.source_file_name = file_name
                existing.source_row_number = int(idx) + 2
                counts["updated"] += 1
            else:
                port_call = BaosPortCall(
                    port_call_id=uuid.uuid4(),
                    port_id=port_id,
                    source_batch_id=batch_id,
                    source_file_name=file_name,
                    source_row_number=int(idx) + 2,
                    source_hash=source_hash,
                    **record,
                )
                db.add(port_call)
                counts["inserted"] += 1

        except Exception as e:
            logger.warning(f"Row {idx + 2}: rejected — {e}")
            counts["rejected"] += 1

    db.flush()
    logger.info(
        f"Port calls: {counts['inserted']} inserted, {counts['updated']} updated, "
        f"{counts['rejected']} rejected, {counts['outlier']} outliers"
    )
    return counts
