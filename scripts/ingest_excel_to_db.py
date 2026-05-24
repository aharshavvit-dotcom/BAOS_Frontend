#!/usr/bin/env python
"""
BAOS Excel-to-DB Ingestion CLI.

Usage:
    python scripts/ingest_excel_to_db.py \
        --port-code INMAA \
        --port-name "Chennai Port" \
        --berth-config sample_data/Berth_configurations.xlsx \
        --berth-capability sample_data/Operational_Capability_of_Berth.xlsx \
        --port-call-log sample_data/Chennai_PORTLOG2025JUN-DEC.xlsx

Also supports CSV:
    python scripts/ingest_excel_to_db.py \
        --port-code INMAA \
        --port-call-log data/Chennai_PORTLOG2025JUN-DEC.csv
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ingest")


def main():
    parser = argparse.ArgumentParser(description="Ingest Excel/CSV data into BAOS database")
    parser.add_argument("--port-code", required=True, help="Port code (e.g. INMAA)")
    parser.add_argument("--port-name", default=None, help="Port display name (e.g. 'Chennai Port')")
    parser.add_argument("--berth-config", default=None, help="Path to Berth_configurations.xlsx")
    parser.add_argument("--berth-capability", default=None, help="Path to Operational_Capability_of_Berth.xlsx")
    parser.add_argument("--port-call-log", default=None, help="Path to port call log (Excel or CSV)")
    args = parser.parse_args()

    port_name = args.port_name or args.port_code

    # ── Setup DB connection ──────────────────────────────────
    from backend.config import settings  # noqa: E402
    from backend.database.connection import SyncSessionFactory, sync_engine  # noqa: E402

    # Ensure baos schema exists
    from sqlalchemy import text
    with sync_engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS baos"))
        conn.commit()

    # Run schema migration
    schema_files = [
        _ROOT / "sql" / "001_create_baos_schema.sql",
        _ROOT / "sql" / "002_seed_assumptions.sql",
        _ROOT / "sql" / "003_create_indexes.sql",
    ]
    with sync_engine.connect() as conn:
        for sf in schema_files:
            if sf.exists():
                logger.info(f"Executing {sf.name}...")
                sql = sf.read_text(encoding="utf-8")
                conn.execute(text(sql))
        conn.commit()
    logger.info("Schema ready")

    # ── Start ingestion ──────────────────────────────────────
    db = SyncSessionFactory()
    try:
        _run_ingestion(db, args, port_name)
        db.commit()
        logger.info("✅ Ingestion completed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


def _run_ingestion(db, args, port_name: str):
    from database.baos_models import BaosPort, IngestionBatch
    from data_ingestion.excel_loader import compute_file_hash
    from data_ingestion.load_berths import load_berths_from_excel
    from data_ingestion.load_capabilities import load_capabilities_from_excel
    from data_ingestion.load_port_calls import load_port_calls_from_file

    # ── 1. Ensure port exists ────────────────────────────────
    port = db.query(BaosPort).filter(BaosPort.port_code == args.port_code).first()
    if not port:
        port = BaosPort(
            port_id=uuid.uuid4(),
            port_code=args.port_code,
            port_name=port_name,
        )
        db.add(port)
        db.flush()
        logger.info(f"Created port: {args.port_code} ({port_name})")
    else:
        logger.info(f"Port exists: {args.port_code} ({port.port_name})")

    port_id = port.port_id
    berth_map = {}
    report = {
        "port_code": args.port_code,
        "port_name": port_name,
        "files": [],
    }

    # ── 2. Ingest berth configurations ───────────────────────
    if args.berth_config:
        path = Path(args.berth_config)
        if not path.exists():
            logger.error(f"File not found: {path}")
        else:
            file_hash = compute_file_hash(path)
            batch = IngestionBatch(
                batch_id=uuid.uuid4(),
                source_file_name=path.name,
                source_file_hash=file_hash,
                source_file_type="excel",
                port_code=args.port_code,
                load_status="RUNNING",
            )
            db.add(batch)
            db.flush()

            berth_map = load_berths_from_excel(db, path, port_id, batch.batch_id)

            batch.load_status = "COMPLETED"
            batch.inserted_rows = len(berth_map)
            batch.total_rows = len(berth_map)
            batch.completed_at = datetime.utcnow()
            db.flush()

            report["files"].append({
                "file": path.name,
                "type": "berth_config",
                "berths_loaded": len(berth_map),
            })
            logger.info(f"Berth config: {len(berth_map)} berths loaded")

    # ── 3. Ingest berth capabilities ─────────────────────────
    if args.berth_capability:
        path = Path(args.berth_capability)
        if not path.exists():
            logger.error(f"File not found: {path}")
        else:
            file_hash = compute_file_hash(path)
            batch = IngestionBatch(
                batch_id=uuid.uuid4(),
                source_file_name=path.name,
                source_file_hash=file_hash,
                source_file_type="excel",
                port_code=args.port_code,
                load_status="RUNNING",
            )
            db.add(batch)
            db.flush()

            cap_count = load_capabilities_from_excel(db, path, port_id, batch.batch_id, berth_map)

            batch.load_status = "COMPLETED"
            batch.inserted_rows = cap_count
            batch.total_rows = cap_count
            batch.completed_at = datetime.utcnow()
            db.flush()

            report["files"].append({
                "file": path.name,
                "type": "berth_capability",
                "capabilities_loaded": cap_count,
            })

    # ── 4. Ingest port call log ──────────────────────────────
    if args.port_call_log:
        path = Path(args.port_call_log)
        if not path.exists():
            logger.error(f"File not found: {path}")
        else:
            file_hash = compute_file_hash(path)
            batch = IngestionBatch(
                batch_id=uuid.uuid4(),
                source_file_name=path.name,
                source_file_hash=file_hash,
                source_file_type="excel" if path.suffix.lower() in (".xlsx", ".xls") else "csv",
                port_code=args.port_code,
                load_status="RUNNING",
            )
            db.add(batch)
            db.flush()

            counts = load_port_calls_from_file(db, path, port_id, batch.batch_id, berth_map)

            batch.load_status = "COMPLETED"
            batch.total_rows = counts["total"]
            batch.inserted_rows = counts["inserted"]
            batch.updated_rows = counts["updated"]
            batch.rejected_rows = counts["rejected"]
            batch.completed_at = datetime.utcnow()
            db.flush()

            report["files"].append({
                "file": path.name,
                "type": "port_call_log",
                **counts,
            })

    # ── 5. Print data quality report ─────────────────────────
    logger.info("=" * 60)
    logger.info("INGESTION REPORT")
    logger.info("=" * 60)
    logger.info(f"Port: {args.port_code} ({port_name})")
    for f in report["files"]:
        logger.info(f"  File: {f['file']} ({f['type']})")
        for k, v in f.items():
            if k not in ("file", "type"):
                logger.info(f"    {k}: {v}")
    logger.info("=" * 60)

    # Save report to file
    report_dir = _ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"ingestion_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Report saved to {report_file}")


if __name__ == "__main__":
    main()
