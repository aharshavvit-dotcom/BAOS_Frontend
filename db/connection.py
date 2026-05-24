"""
Database Connection — PostgreSQL connection pooling.
Connects to the ML_APP database at localhost:5433.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Generator, Optional

try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# ── Connection Config ──────────────────────────────────────────────────────

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "ML_APP",
    "user": "postgres",
    "password": "postgres@123",
}

DSN = (
    f"host={DB_CONFIG['host']} "
    f"port={DB_CONFIG['port']} "
    f"dbname={DB_CONFIG['dbname']} "
    f"user={DB_CONFIG['user']} "
    f"password={DB_CONFIG['password']}"
)

_pool: Optional["pg_pool.SimpleConnectionPool"] = None


def _get_pool() -> "pg_pool.SimpleConnectionPool":
    global _pool
    if _pool is None or _pool.closed:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError(
                "psycopg2 is not installed. Run: pip install psycopg2-binary"
            )
        _pool = pg_pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            **DB_CONFIG,
        )
    return _pool


@contextmanager
def get_connection() -> Generator:
    """
    Context manager that yields a PostgreSQL connection.
    Automatically returns connection to pool on exit.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def test_connection() -> bool:
    """Return True if database is reachable, False otherwise."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"[DB] Connection test failed: {e}", file=sys.stderr)
        return False


def close_pool() -> None:
    """Gracefully close all connections in the pool."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
    _pool = None
