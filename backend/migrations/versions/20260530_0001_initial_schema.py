"""Initial BAOS schema.

Revision ID: 20260530_0001
Revises:
Create Date: 2026-05-30
"""
from __future__ import annotations

from pathlib import Path

from alembic import op
from sqlalchemy import text

from backend.db.session import Base

import backend.db.models.app_models  # noqa: F401
import backend.db.models.baos_models  # noqa: F401

revision = "20260530_0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def _run_sql_file(name: str) -> None:
    sql = (SQL_DIR / name).read_text(encoding="utf-8").strip()
    if sql:
        op.execute(text(sql))


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(text("CREATE SCHEMA IF NOT EXISTS baos"))
    _run_sql_file("001_create_baos_schema.sql")
    _run_sql_file("002_seed_assumptions.sql")
    _run_sql_file("003_create_indexes.sql")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute(text("DROP SCHEMA IF EXISTS baos CASCADE"))
