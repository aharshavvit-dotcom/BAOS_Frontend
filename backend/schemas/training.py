"""Pydantic schemas for training endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

# FIX (Phase 4): Training endpoints used response_model=dict -> define typed status schemas.


class TrainingStatusResponse(BaseModel):
    in_progress: bool
    lock_held: bool

    model_config = ConfigDict(from_attributes=True)


class TrainingStartResponse(TrainingStatusResponse):
    status: str

    model_config = ConfigDict(from_attributes=True)


class TrainingRunOut(BaseModel):
    # FIX (Phase 5): Expose persisted train/validation scores for auditability.
    id: int
    model_name: str
    version: int
    trained_at: datetime | None = None
    train_score: float | None = None
    val_score: float | None = None
    data_rows: int | None = None
    feature_hash: str | None = None
    hyperparameters: dict[str, Any] | None = None
    status: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
