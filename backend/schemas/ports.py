"""Pydantic schemas for port endpoints."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.berths import BerthOut
from backend.schemas.common import PaginatedResponse

# FIX (Phase 4): Port endpoints exposed raw dict/list shapes -> define validated API schemas.


class ModelInfoOut(BaseModel):
    model_version: str | None = None
    training_date: str | None = None
    training_rows: int | None = None
    features_used: list[str] = Field(default_factory=list)
    feature_count: int = 0
    split_strategy: str | None = None
    metrics: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class PortSummaryOut(BaseModel):
    port_name: str
    port_code: str
    trained: bool
    training_status: str
    status_label: str
    training_message: str
    num_berths: int
    history_rows: int
    valid_training_rows: int
    models_missing: list[str] = Field(default_factory=list)
    models_stale: list[str] = Field(default_factory=list)
    model_info: ModelInfoOut | None = None

    model_config = ConfigDict(from_attributes=True)


class PortListResponse(PaginatedResponse[PortSummaryOut]):
    model_config = ConfigDict(from_attributes=True)


class DataQualityOut(BaseModel):
    overall_score: float
    source: str
    completeness_pct: float
    recency_days: int

    model_config = ConfigDict(from_attributes=True)


class PortStatusOut(PortSummaryOut):
    has_enough_data: bool
    is_stale: bool
    models_required: list[str] = Field(default_factory=list)
    models_active: list[str] = Field(default_factory=list)
    data_quality: DataQualityOut
    berth_count: int
    capability_count: int
    berth_class_count: int
    latest_data_ts: str | None = None
    data_start_ts: str | None = None
    data_end_ts: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceTimeStatOut(BaseModel):
    port_code: str
    berth_code: str | None = None
    vessel_type: str | None = None
    count: int = 0
    service_hours_median: float = 0.0
    service_hours_mean: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class PortConfigOut(BaseModel):
    port_name: str
    port_code: str
    planning_start: str = ""
    num_berths: int
    berths: list[BerthOut] = Field(default_factory=list)
    service_time_stats: list[ServiceTimeStatOut] = Field(default_factory=list)
    assumptions: dict[str, float] = Field(default_factory=dict)
    vessel_types: list[str] = Field(default_factory=list)
    cargo_types: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
