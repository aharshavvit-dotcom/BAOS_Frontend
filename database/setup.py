"""Database setup — programmatically creates the `baos` database if it doesn't exist.

Usage:
    python -m database.setup

Connects to the default `postgres` database to check/create the `baos` database,
then validates the connection to `baos` is successful.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
_ROOT = Path(__file__).resolve().parent.parent
for _path in (_BACKEND, _ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from backend.config import settings


def _build_admin_url() -> URL:
    """Build a connection URL to the default `postgres` database for admin ops."""
    return URL.create(
        drivername="postgresql+psycopg2",
        username=settings.DB_USER,
        password=settings.DB_PASS,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database="postgres",
    )


def ensure_database() -> None:
    """Create the `baos` database if it does not already exist."""
    target_db = settings.DB_NAME  # FIX: Must be 'baos', not 'ML_APP'
    admin_url = _build_admin_url()
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": target_db},
        )
        exists = result.scalar() is not None

    if exists:
        print(f"[setup] Database '{target_db}' already exists.")
    else:
        print(f"[setup] Creating database '{target_db}'...")
        with admin_engine.connect() as conn:
            # FIX: Programmatically create the baos database instead of relying on manual psql
            conn.execute(text(f'CREATE DATABASE "{target_db}"'))
        print(f"[setup] Database '{target_db}' created successfully.")

    admin_engine.dispose()

    # Validate the connection to the new database works
    target_engine = create_engine(settings.DATABASE_URL_SYNC)
    with target_engine.connect() as conn:
        result = conn.execute(text("SELECT current_database()"))
        current = result.scalar()
        print(f"[setup] Connected to database: {current}")
    target_engine.dispose()


if __name__ == "__main__":
    ensure_database()
