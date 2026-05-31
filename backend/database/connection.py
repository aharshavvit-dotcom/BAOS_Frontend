"""Standalone SQLAlchemy connection primitives.

This module intentionally imports only stdlib and SQLAlchemy so legacy imports
cannot form a circular dependency through application config or ORM models.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://baos_user:baos_pass@localhost:5432/baos_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
