"""
Application Configuration — loads from .env via Pydantic BaseSettings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # ── Database (individual parts to avoid URL-encoding issues) ──
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres@123"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5433
    DB_NAME: str = "baos"  # FIX: Renamed from 'ML_APP' → 'baos' to match the schema namespace

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
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
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
    APP_ENV: str = "development"
    APP_PORT: int = 8001
    DEBUG: bool = True

    # ML and defaults
    MODEL_ARTIFACTS_DIR: str = "model_artifacts"
    MIN_TRAINING_ROWS: int = 100
    DEFAULT_PORT_CODE: str = "INMAA"
    # FIX (Phase 5): Keep inferred berth limits conservative and configurable instead of cloning history maxima.
    BERTH_LIMIT_INFERENCE_FACTOR: float = 0.95
    # FIX (Phase 5): Centralize deterministic training controls used by every ML pipeline.
    ML_RANDOM_STATE: int = 42
    ML_VALIDATION_SIZE: float = 0.20
    KPI_DEFAULT_DAYS: int = 90
    # FIX (Phase 5): RL reward weights are explicit knobs while the agent remains experimental.
    RL_DELAY_WEIGHT: float = 1.0
    RL_IDLE_WEIGHT: float = 0.3
    RL_MISMATCH_WEIGHT: float = 0.5
    # FIX (Phase 7): Centralize currency for cost engine — was hardcoded as USD.
    CURRENCY_CODE: str = "INR"
    CURRENCY_SYMBOL: str = "₹"
    PORT_CHARGES_PER_HOUR: float = 100.0
    # FIX (Phase 5): Tide data configuration — synthetic by default.
    USE_REAL_TIDE_DATA: bool = False
    TIDE_DATA_PATH: str = ""
    BERTH_DEPTH_BUFFER: float = 1.5  # Metres of under-keel clearance required

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str):
        if not value:
            raise ValueError(
                "JWT_SECRET_KEY is required. Generate one with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters.")
        if value == "baos-ai-super-secret-key-change-in-production-2026":
            raise ValueError("JWT_SECRET_KEY must not use the bundled development default.")
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes", "on"}:
                return True
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    @property
    def database_url(self) -> str:
        return str(self.DATABASE_URL)

    @property
    def jwt_secret(self) -> str:
        return self.JWT_SECRET_KEY

    @property
    def jwt_algorithm(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def jwt_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def allowed_origins(self) -> str:
        return self.CORS_ORIGINS

    @property
    def app_env(self) -> str:
        return self.APP_ENV

    @property
    def app_port(self) -> int:
        return self.APP_PORT

    @property
    def model_artifacts_dir(self) -> str:
        return self.MODEL_ARTIFACTS_DIR

    @property
    def min_training_rows(self) -> int:
        return self.MIN_TRAINING_ROWS

    @property
    def default_port_code(self) -> str:
        return self.DEFAULT_PORT_CODE

    @property
    def berth_limit_inference_factor(self) -> float:
        return self.BERTH_LIMIT_INFERENCE_FACTOR

    @property
    def ml_random_state(self) -> int:
        return self.ML_RANDOM_STATE

    @property
    def ml_validation_size(self) -> float:
        return self.ML_VALIDATION_SIZE

    @property
    def kpi_default_days(self) -> int:
        return self.KPI_DEFAULT_DAYS

    @property
    def training_hyperparameters(self) -> dict:
        # FIX (Phase 5): Persist the effective training knobs with each training run.
        return {
            "min_training_rows": self.MIN_TRAINING_ROWS,
            "validation_size": self.ML_VALIDATION_SIZE,
            "random_state": self.ML_RANDOM_STATE,
        }

    model_config = ConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
