"""
Database seed script — populates initial data for development.
Run: python -m database.seed
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SyncSession

try:
    from backend.config import settings
except ImportError:
    from config import settings
from database.connection import Base
from database.models import Port, Berth, User, KPI
from auth.password import hash_password


def seed():
    """Create tables and insert seed data using sync engine."""
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    print("[Seed] Creating tables...")
    Base.metadata.create_all(engine)

    with SyncSession(engine) as session:
        # ── Ports ────────────────────────────────────────────────────────
        print("[Seed] Checking for existing port...")

        existing_port = session.execute(select(Port).where(Port.code == "INMAA")).scalar_one_or_none()
        if existing_port is None:
            chennai = Port(
                name="Chennai",
                code="INMAA",
                country="India",
                config_json={"timezone": "Asia/Kolkata", "currency": "INR"},
            )
            session.add(chennai)
            session.flush()

            # ── Berths ──────────────────────────────────────────────────
            print("[Seed] Inserting berths...")
            berths_data = [
                {"code": "INMAA-B01", "name": "Berth A1 — Container Terminal", "terminal_code": "CT", "terminal_name": "Container Terminal", "max_loa_m": 350, "max_draft_m": 14.5, "max_beam_m": 48, "allowed_vessel_types": ["Container Ship"]},
                {"code": "INMAA-B02", "name": "Berth A2 — Container Terminal", "terminal_code": "CT", "terminal_name": "Container Terminal", "max_loa_m": 300, "max_draft_m": 13.0, "max_beam_m": 45, "allowed_vessel_types": ["Container Ship"]},
                {"code": "INMAA-B03", "name": "Berth B1 — Bulk Terminal", "terminal_code": "BT", "terminal_name": "Bulk Terminal", "max_loa_m": 280, "max_draft_m": 12.5, "max_beam_m": 42, "allowed_vessel_types": ["Bulk Carrier", "General Cargo"]},
                {"code": "INMAA-B04", "name": "Berth B2 — Bulk Terminal", "terminal_code": "BT", "terminal_name": "Bulk Terminal", "max_loa_m": 260, "max_draft_m": 11.0, "max_beam_m": 38, "allowed_vessel_types": ["Bulk Carrier", "General Cargo"]},
                {"code": "INMAA-B05", "name": "Berth C1 — Oil Terminal", "terminal_code": "OT", "terminal_name": "Oil Terminal", "max_loa_m": 320, "max_draft_m": 16.0, "max_beam_m": 50, "allowed_vessel_types": ["Crude Oil Tanker", "Chemical Tanker"]},
                {"code": "INMAA-B06", "name": "Berth D1 — Multi-purpose", "terminal_code": "MP", "terminal_name": "Multi-purpose Terminal", "max_loa_m": 250, "max_draft_m": 10.5, "max_beam_m": 35, "allowed_vessel_types": ["General Cargo", "RoRo", "Container Ship"]},
                {"code": "INMAA-B07", "name": "Berth D2 — Multi-purpose", "terminal_code": "MP", "terminal_name": "Multi-purpose Terminal", "max_loa_m": 220, "max_draft_m": 10.0, "max_beam_m": 33, "allowed_vessel_types": ["General Cargo", "RoRo"]},
            ]

            for b in berths_data:
                session.add(Berth(
                    port_id=chennai.id,
                    code=b["code"],
                    name=b["name"],
                    terminal_code=b.get("terminal_code", ""),
                    terminal_name=b.get("terminal_name", ""),
                    max_loa_m=b.get("max_loa_m", 300),
                    max_draft_m=b.get("max_draft_m", 14),
                    max_beam_m=b.get("max_beam_m", 45),
                    depth_m=b.get("max_draft_m", 14) * 1.15,
                    allowed_vessel_types=b.get("allowed_vessel_types", []),
                    equipment_types=["crane", "hose", "gangway"],
                ))

            # ── Demo User ───────────────────────────────────────────────
            print("[Seed] Inserting demo user...")
            existing_user = session.execute(
                select(User).where(User.email == "admin@baos.ai")
            ).scalar_one_or_none()
            if existing_user is None:
                session.add(User(
                    email="admin@baos.ai",
                    password_hash=hash_password("admin123"),
                    full_name="Port Manager",
                    company="Chennai Port Authority",
                    port_id=chennai.id,
                    role="admin",
                ))

            # ── Sample KPI ──────────────────────────────────────────────
            print("[Seed] Inserting sample KPI...")
            session.add(KPI(
                port_id=chennai.id,
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
            ))

        session.commit()
        print("[Seed] Database seeded successfully!")


if __name__ == "__main__":
    seed()
