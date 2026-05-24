"""
Application Configuration — loads from .env via Pydantic BaseSettings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # ── Database (individual parts to avoid URL-encoding issues) ──
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres@123"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5433
    DB_NAME: str = "ML_APP"

    def get_database_url(self, driver: str = "postgresql+asyncpg") -> URL:
        """Build a SQLAlchemy URL object that properly escapes special chars."""
        return URL.create(
            drivername=driver,
            username=self.DB_USER,
            password=self.DB_PASS,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def DATABASE_URL(self) -> URL:
        """Async connection URL (psycopg) — returns URL object."""
        return self.get_database_url("postgresql+asyncpg")

    @property
    def DATABASE_URL_SYNC(self) -> URL:
        """Sync connection URL (psycopg2) — returns URL object."""
        return self.get_database_url("postgresql+psycopg2")

    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY: str = "baos-ai-super-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis / Celery ────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8501","http://127.0.0.1:3000"]'

    # ── App ───────────────────────────────────────────────
    APP_NAME: str = "BAOS AI - Maritime Decision Intelligence"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    class Config:
        env_file = str(Path(__file__).resolve().parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
