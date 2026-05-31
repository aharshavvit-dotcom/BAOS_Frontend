"""
Database seed script.

Run from the repository root:
    python -m database.seed

The seed is intentionally idempotent. It creates the legacy auth/dashboard
tables, creates the baos schema, loads the bundled sample Excel data into
baos.berth, baos.berth_capability and baos.port_call, and ensures known users
exist with bcrypt password hashes.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, text

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent
for _path in (_BACKEND, _ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from backend.auth.password import hash_password, verify_password
from backend.db.session import Base, SyncSessionFactory, sync_engine
from backend.db.models.app_models import Berth, KPI, Port, User


PORT_CODE = "INMAA"
PORT_NAME = "Chennai Port"
LEGACY_PORT_NAME = "Chennai"
ADMIN_EMAIL = "admin@baos.ai"
ADMIN_PASSWORD = "admin123"
OPERATOR_EMAIL = "operator@baos.ai"
OPERATOR_PASSWORD = "operator123"


def _run_sql_file(path: Path) -> None:
    if not path.exists():
        print(f"[Seed] Skipping missing SQL file: {path}")
        return
    with sync_engine.connect() as conn:
        conn.execute(text(path.read_text(encoding="utf-8")))
        conn.commit()


def _create_schema() -> None:
    import backend.db.models.baos_models  # noqa: F401

    print("[Seed] Creating schemas and tables...")
    with sync_engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS baos"))
        conn.commit()

    for sql_file in (
        _BACKEND / "migrations" / "sql" / "001_create_baos_schema.sql",
        _BACKEND / "migrations" / "sql" / "002_seed_assumptions.sql",
        _BACKEND / "migrations" / "sql" / "003_create_indexes.sql",
    ):
        _run_sql_file(sql_file)

    Base.metadata.create_all(sync_engine)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _ensure_legacy_port_and_berths(session) -> Port:
    port = session.execute(select(Port).where(Port.code == PORT_CODE)).scalar_one_or_none()
    if port is None:
        port = Port(
            name=LEGACY_PORT_NAME,
            code=PORT_CODE,
            country="India",
            config_json={"timezone": "Asia/Kolkata", "currency": "INR"},
        )
        session.add(port)
        session.flush()
    else:
        port.name = LEGACY_PORT_NAME
        port.country = "India"
        port.config_json = {**(port.config_json or {}), "timezone": "Asia/Kolkata", "currency": "INR"}

    existing_count = session.execute(
        select(func.count(Berth.id)).where(Berth.port_id == port.id)
    ).scalar_one()
    if existing_count:
        return port

    print("[Seed] Inserting legacy berth master records...")
    berths_data = [
        ("INMAA-B01", "Container Terminal A1", "CT", "Container Terminal", 350, 48, 14.5, ["Container Ship"]),
        ("INMAA-B02", "Container Terminal A2", "CT", "Container Terminal", 300, 45, 13.0, ["Container Ship"]),
        ("INMAA-B03", "Bulk Terminal B1", "BT", "Bulk Terminal", 280, 42, 12.5, ["Bulk Carrier", "General Cargo"]),
        ("INMAA-B04", "Bulk Terminal B2", "BT", "Bulk Terminal", 260, 38, 11.0, ["Bulk Carrier", "General Cargo"]),
        ("INMAA-B05", "Oil Terminal C1", "OT", "Oil Terminal", 320, 50, 16.0, ["Crude Oil Tanker", "Chemical Tanker"]),
        ("INMAA-B06", "Multi-purpose D1", "MP", "Multi-purpose Terminal", 250, 35, 10.5, ["General Cargo", "RoRo", "Container Ship"]),
        ("INMAA-B07", "Multi-purpose D2", "MP", "Multi-purpose Terminal", 220, 33, 10.0, ["General Cargo", "RoRo"]),
    ]
    for code, name, terminal_code, terminal_name, loa, beam, draft, vessel_types in berths_data:
        session.add(
            Berth(
                port_id=port.id,
                code=code,
                name=name,
                terminal_code=terminal_code,
                terminal_name=terminal_name,
                max_loa_m=loa,
                max_beam_m=beam,
                max_draft_m=draft,
                depth_m=draft * 1.15,
                allowed_vessel_types=vessel_types,
                equipment_types=["crane", "hose", "gangway"],
            )
        )
    return port


def _ensure_user(session, *, email: str, password: str, full_name: str, role: str, port_id) -> None:
    normalized = _normalize_email(email)
    user = session.execute(
        select(User).where(func.lower(User.email) == normalized)
    ).scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=normalized,
            password_hash=hash_password(password),
            full_name=full_name,
            company=PORT_NAME,
            port_id=port_id,
            role=role,
            is_active=True,
        )
        session.add(user)
        print(f"[Seed] Created {role} user: {normalized}")
    else:
        user.email = normalized
        user.full_name = full_name
        user.company = PORT_NAME
        user.port_id = port_id
        user.role = role
        user.is_active = True
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
        print(f"[Seed] Ensured {role} user: {normalized}")


def _ensure_legacy_kpi(session, port_id) -> None:
    existing = session.execute(
        select(KPI).where(KPI.port_id == port_id).order_by(KPI.date.desc()).limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return

    session.add(
        KPI(
            port_id=port_id,
            date=datetime.now(timezone.utc),
            vessels_count=142,
            revenue=480000,
            cost=230000,
            utilization_pct=78.0,
            sla_compliance_pct=94.0,
            avg_turnaround_hours=26.5,
            data_json={
                "monthly_vessels": [120, 131, 142],
                "monthly_revenue": [380000, 420000, 480000],
            },
        )
    )


def _load_sample_data(session) -> None:
    from backend.db.models.baos_models import BaosPort, IngestionBatch
    from engines.ingestion.excel_loader import compute_file_hash
    from engines.ingestion.load_berths import load_berths_from_excel
    from engines.ingestion.load_capabilities import load_capabilities_from_excel
    from engines.ingestion.load_port_calls import load_port_calls_from_file

    sample_dir = _ROOT / "sample_data"
    berth_config = sample_dir / "Berth_configurations.xlsx"
    berth_capability = sample_dir / "Operational_Capability_of_Berth.xlsx"
    port_call_log = sample_dir / "Chennai_PORTLOG2025JUN-DEC.xlsx"

    missing = [p for p in (berth_config, berth_capability, port_call_log) if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing sample data files: " + ", ".join(str(p) for p in missing))

    port = session.execute(
        select(BaosPort).where(BaosPort.port_code == PORT_CODE)
    ).scalar_one_or_none()
    if port is None:
        port = BaosPort(
            port_id=uuid.UUID("a0000000-0000-0000-0000-000000000001"),
            port_code=PORT_CODE,
            port_name=PORT_NAME,
            country="India",
            timezone="Asia/Kolkata",
        )
        session.add(port)
        session.flush()
    else:
        port.port_name = PORT_NAME
        port.country = "India"
        port.timezone = "Asia/Kolkata"
        port.is_active = True

    print("[Seed] Loading sample berth configuration...")
    berth_batch = IngestionBatch(
        batch_id=uuid.uuid4(),
        source_file_name=berth_config.name,
        source_file_hash=compute_file_hash(berth_config),
        source_file_type="excel",
        port_code=PORT_CODE,
        load_status="RUNNING",
    )
    session.add(berth_batch)
    session.flush()
    berth_map = load_berths_from_excel(session, berth_config, port.port_id, berth_batch.batch_id)
    berth_batch.load_status = "COMPLETED"
    berth_batch.total_rows = len(berth_map)
    berth_batch.inserted_rows = len(berth_map)
    berth_batch.completed_at = datetime.utcnow()

    print("[Seed] Loading sample berth capabilities...")
    capability_batch = IngestionBatch(
        batch_id=uuid.uuid4(),
        source_file_name=berth_capability.name,
        source_file_hash=compute_file_hash(berth_capability),
        source_file_type="excel",
        port_code=PORT_CODE,
        load_status="RUNNING",
    )
    session.add(capability_batch)
    session.flush()
    capability_count = load_capabilities_from_excel(
        session,
        berth_capability,
        port.port_id,
        capability_batch.batch_id,
        berth_map,
    )
    capability_batch.load_status = "COMPLETED"
    capability_batch.total_rows = capability_count
    capability_batch.inserted_rows = capability_count
    capability_batch.completed_at = datetime.utcnow()

    print("[Seed] Loading sample port-call history...")
    port_call_batch = IngestionBatch(
        batch_id=uuid.uuid4(),
        source_file_name=port_call_log.name,
        source_file_hash=compute_file_hash(port_call_log),
        source_file_type="excel",
        port_code=PORT_CODE,
        load_status="RUNNING",
    )
    session.add(port_call_batch)
    session.flush()
    counts = load_port_calls_from_file(
        session,
        port_call_log,
        port.port_id,
        port_call_batch.batch_id,
        berth_map,
    )
    port_call_batch.load_status = "COMPLETED"
    port_call_batch.total_rows = counts["total"]
    port_call_batch.inserted_rows = counts["inserted"]
    port_call_batch.updated_rows = counts["updated"]
    port_call_batch.rejected_rows = counts["rejected"]
    port_call_batch.completed_at = datetime.utcnow()

    print(
        "[Seed] Sample data loaded: "
        f"{len(berth_map)} berths, {capability_count} capabilities, "
        f"{counts['inserted']} port calls inserted, {counts['updated']} updated, "
        f"{counts['rejected']} rejected."
    )


def seed() -> None:
    _create_schema()

    session = SyncSessionFactory()
    try:
        existing_count = session.execute(
            text("SELECT COUNT(*) FROM baos.port_call")
        ).scalar()
        if existing_count > 0:
            print(f"[seed] Skipping - {existing_count} port_call rows already exist.")
            return {
                "status": "skipped",
                "reason": "data already present",
                "existing_rows": existing_count,
            }
        print("[seed] No existing data found. Proceeding with seed...")

        legacy_port = _ensure_legacy_port_and_berths(session)
        _ensure_user(
            session,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            full_name="Port Administrator",
            role="admin",
            port_id=legacy_port.id,
        )
        _ensure_user(
            session,
            email=OPERATOR_EMAIL,
            password=OPERATOR_PASSWORD,
            full_name="Port Operator",
            role="operator",
            port_id=legacy_port.id,
        )
        _ensure_legacy_kpi(session, legacy_port.id)
        _load_sample_data(session)
        session.commit()
        print("[Seed] Database seeded successfully.")
        print(f"[Seed] Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
