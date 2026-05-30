"""
Excel / CSV Loader — reads files, computes hashes, creates batches.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: str | Path) -> str:
    """SHA-256 hash of the file contents."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_row_hash(row_data: dict) -> str:
    """SHA-1 hash of a row's data for deduplication."""
    key = json.dumps(row_data, sort_keys=True, default=str)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def read_file(file_path: str | Path, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    """
    Read an Excel or CSV file.

    Returns:
        (DataFrame, detected_file_type)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet_name or 0)
        file_type = "excel"
    elif ext == ".csv":
        df = pd.read_csv(path)
        file_type = "csv"
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    logger.info(f"Read {len(df)} rows × {len(df.columns)} cols from {path.name}")
    return df, file_type


def create_batch_record(
    file_path: str | Path,
    port_code: str,
    file_hash: str,
    file_type: str,
) -> dict:
    """Create an ingestion_batch record dict (to be inserted into DB)."""
    return {
        "batch_id": uuid.uuid4(),
        "source_file_name": Path(file_path).name,
        "source_file_hash": file_hash,
        "source_file_type": file_type,
        "port_code": port_code,
        "load_status": "RUNNING",
        "total_rows": 0,
        "inserted_rows": 0,
        "updated_rows": 0,
        "rejected_rows": 0,
        "started_at": datetime.utcnow(),
    }
