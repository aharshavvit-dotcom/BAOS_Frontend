"""Apply root SQL migrations (FKs, indexes, audit timestamps, model versioning).

Revision ID: 20260531_0002
Revises: 20260530_0001
Create Date: 2026-05-31
"""
from __future__ import annotations

from pathlib import Path
from alembic import op
from sqlalchemy import text

revision = "20260531_0002"
down_revision = "20260530_0001"
branch_labels = None
depends_on = None

SQL_DIR = Path(__file__).resolve().parents[3] / "sql" / "migrations"


def _run_sql_file(name: str) -> None:
    file_path = SQL_DIR / name
    sql = file_path.read_text(encoding="utf-8").strip()
    if sql:
        op.execute(text(sql))


def upgrade() -> None:
    # Run the SQL migration files from the root sql/migrations directory in order
    _run_sql_file("001_add_fk_constraints.sql")
    _run_sql_file("002_add_indexes.sql")
    _run_sql_file("003_add_audit_timestamps.sql")
    _run_sql_file("004_add_model_versioning.sql")


def downgrade() -> None:
    # Downgrade: Drop training_runs table
    op.execute(text("DROP TABLE IF EXISTS baos.training_runs CASCADE"))
