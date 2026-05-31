"""Run pending SQL migrations in order.

Usage:
    python -m database.run_migrations
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from backend.config import settings

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "sql" / "migrations"

engine = create_engine(settings.DATABASE_URL_SYNC)


def ensure_migrations_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     VARCHAR(10) PRIMARY KEY,
            filename    VARCHAR(255) NOT NULL,
            applied_at  TIMESTAMPTZ DEFAULT NOW(),
            checksum    VARCHAR(64) NOT NULL
        )
    """))
    conn.commit()


def get_applied_versions(conn) -> set[str]:
    result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
    return {row[0] for row in result}


def run_migrations() -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("[migrations] No migration files found.")
        return

    with engine.connect() as conn:
        ensure_migrations_table(conn)
        applied = get_applied_versions(conn)

        for filepath in migration_files:
            filename = filepath.name
            version = filename.split("_", 1)[0]

            if version in applied:
                print(f"[migrations] {filename} - already applied, skipping.")
                continue

            print(f"[migrations] Applying {filename}...")
            sql = filepath.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]

            try:
                conn.execute(text(sql))
                conn.execute(
                    text("""
                        INSERT INTO schema_migrations (version, filename, checksum)
                        VALUES (:version, :filename, :checksum)
                    """),
                    {
                        "version": version,
                        "filename": filename,
                        "checksum": checksum,
                    },
                )
                conn.commit()
                print(f"[migrations] {filename} - applied successfully.")
            except Exception as exc:
                conn.rollback()
                print(f"[migrations] ERROR applying {filename}: {exc}")
                sys.exit(1)

    print("[migrations] All migrations complete.")


if __name__ == "__main__":
    run_migrations()
