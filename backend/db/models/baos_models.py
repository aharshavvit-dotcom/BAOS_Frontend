"""
BAOS Domain ORM Models — baos.* schema.

All core domain tables: ports, berths, capabilities, port calls,
assumptions, ML model registry, optimization, recommendations.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, BigInteger, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


def _uuid():
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────────────────────
#  Ingestion Batch
# ─────────────────────────────────────────────────────────────────────────────

class IngestionBatch(Base):
    __tablename__ = "ingestion_batch"
    __table_args__ = {"schema": "baos"}

    batch_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_file_name = Column(Text, nullable=False)
    source_file_hash = Column(Text, nullable=False)
    source_file_type = Column(Text)
    port_code = Column(Text)
    load_status = Column(Text, nullable=False, default="PENDING")
    total_rows = Column(Integer, default=0)
    inserted_rows = Column(Integer, default=0)
    updated_rows = Column(Integer, default=0)
    rejected_rows = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


# ─────────────────────────────────────────────────────────────────────────────
#  Port
# ─────────────────────────────────────────────────────────────────────────────

class BaosPort(Base):
    __tablename__ = "port"
    __table_args__ = {"schema": "baos"}

    port_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_code = Column(Text, unique=True, nullable=False, index=True)
    port_name = Column(Text, nullable=False)
    country = Column(Text, default="India")
    timezone = Column(Text, default="Asia/Kolkata")
    latitude = Column(Float)
    longitude = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    berths = relationship("BaosBerth", back_populates="port", cascade="all, delete-orphan")
    port_calls = relationship("BaosPortCall", back_populates="port")
    assumptions = relationship("BaosAssumptionConfig", back_populates="port")
    models = relationship("BaosMLModelRegistry", back_populates="port")


# ─────────────────────────────────────────────────────────────────────────────
#  Berth
# ─────────────────────────────────────────────────────────────────────────────

class BaosBerth(Base):
    __tablename__ = "berth"
    __table_args__ = (
        {"schema": "baos"},
    )

    berth_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("baos.port.port_id"), nullable=False)
    berth_code = Column(Text, nullable=False)
    berth_name = Column(Text)
    terminal_name = Column(Text)
    berth_class = Column(Text)
    max_loa_m = Column(Float)
    max_beam_m = Column(Float)
    max_draft_m = Column(Float)
    depth_m = Column(Float)
    length_m = Column(Float)
    is_active = Column(Boolean, default=True)
    data_quality_level = Column(Text, default="SPEC")
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("baos.ingestion_batch.batch_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    port = relationship("BaosPort", back_populates="berths")
    capabilities = relationship("BaosBerthCapability", back_populates="berth", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
#  Berth Capability
# ─────────────────────────────────────────────────────────────────────────────

class BaosBerthCapability(Base):
    __tablename__ = "berth_capability"
    __table_args__ = {"schema": "baos"}

    capability_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    berth_id = Column(UUID(as_uuid=True), ForeignKey("baos.berth.berth_id"), nullable=False)
    vessel_type = Column(Text)
    cargo_type = Column(Text)
    equipment_type = Column(Text)
    equipment_count = Column(Integer)
    handling_rate_tons_per_hour = Column(Float)
    priority_level = Column(Integer, default=0)
    is_preferred = Column(Boolean, default=False)
    capability_score = Column(Float)
    data_quality_level = Column(Text, default="SPEC")
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("baos.ingestion_batch.batch_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    berth = relationship("BaosBerth", back_populates="capabilities")


# ─────────────────────────────────────────────────────────────────────────────
#  Port Call (Historical)
# ─────────────────────────────────────────────────────────────────────────────

class BaosPortCall(Base):
    __tablename__ = "port_call"
    __table_args__ = {"schema": "baos"}

    port_call_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("baos.port.port_id"), nullable=False)

    vessel_name = Column(Text)
    vessel_imo = Column(Text)
    vessel_type = Column(Text)
    cargo_type = Column(Text)

    berth_id = Column(UUID(as_uuid=True), ForeignKey("baos.berth.berth_id"))
    berth_code_raw = Column(Text)

    loa_m = Column(Float)
    beam_m = Column(Float)
    arrival_draft_m = Column(Float)
    departure_draft_m = Column(Float)
    dwt = Column(Float)
    cargo_tons = Column(Float)

    eosp_ts = Column(DateTime)
    pob_ts = Column(DateTime)
    all_fast_ts = Column(DateTime)
    last_line_ts = Column(DateTime)
    cosp_ts = Column(DateTime)

    pilot_wait_hours = Column(Float)
    pilot_to_berth_hours = Column(Float)
    berth_occupancy_hours = Column(Float)
    unberth_outbound_hours = Column(Float)
    total_port_stay_hours = Column(Float)

    is_valid_for_training = Column(Boolean, default=True)
    validation_status = Column(Text, default="VALID")
    validation_notes = Column(Text)

    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("baos.ingestion_batch.batch_id"))
    source_file_name = Column(Text)
    source_sheet_name = Column(Text)
    source_row_number = Column(Integer)
    source_hash = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    port = relationship("BaosPort", back_populates="port_calls")


# ─────────────────────────────────────────────────────────────────────────────
#  Assumption Configuration
# ─────────────────────────────────────────────────────────────────────────────

class BaosAssumptionConfig(Base):
    __tablename__ = "assumption_config"
    __table_args__ = {"schema": "baos"}

    assumption_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("baos.port.port_id"))
    assumption_key = Column(Text, nullable=False)
    assumption_value = Column(Float, nullable=False)
    unit = Column(Text)
    source_quality = Column(Text, default="ASSUMPTION")
    confidence_multiplier = Column(Float, default=0.80)
    description = Column(Text)
    used_in_decision = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    port = relationship("BaosPort", back_populates="assumptions")


# ─────────────────────────────────────────────────────────────────────────────
#  ML Model Registry
# ─────────────────────────────────────────────────────────────────────────────

class BaosMLModelRegistry(Base):
    __tablename__ = "ml_model_registry"
    __table_args__ = {"schema": "baos"}

    model_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("baos.port.port_id"), nullable=False)
    model_name = Column(Text, nullable=False)
    model_type = Column(Text, nullable=False)
    target_name = Column(Text, nullable=False)
    model_version = Column(Text, nullable=False)
    artifact_path = Column(Text)
    feature_schema = Column(JSON)
    metrics = Column(JSON)
    baseline_metrics = Column(JSON)
    training_start_ts = Column(DateTime)
    training_end_ts = Column(DateTime)
    training_rows = Column(Integer)
    validation_rows = Column(Integer)
    test_rows = Column(Integer)
    split_strategy = Column(Text)
    data_start_ts = Column(DateTime)
    data_end_ts = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    port = relationship("BaosPort", back_populates="models")


# ─────────────────────────────────────────────────────────────────────────────
#  Optimization Run
# ─────────────────────────────────────────────────────────────────────────────

class BaosOptimizationRun(Base):
    __tablename__ = "optimization_run"
    __table_args__ = {"schema": "baos"}

    optimization_run_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("baos.port.port_id"), nullable=False)
    scenario_name = Column(Text)
    solver_status = Column(Text)
    objective_value = Column(Float)
    total_wait_hours = Column(Float)
    total_cost_usd = Column(Float)
    assigned_count = Column(Integer)
    unassigned_count = Column(Integer)
    config = Column(JSON)
    assumptions_used = Column(JSON)
    request_payload = Column(JSON)
    result_summary = Column(JSON)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    assignments = relationship("BaosOptimizationAssignment", back_populates="run", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
#  Optimization Assignment
# ─────────────────────────────────────────────────────────────────────────────

class BaosOptimizationAssignment(Base):
    __tablename__ = "optimization_assignment"
    __table_args__ = {"schema": "baos"}

    assignment_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    optimization_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("baos.optimization_run.optimization_run_id"),
        nullable=False,
    )
    vessel_temp_id = Column(Text, nullable=False)
    vessel_name = Column(Text)
    berth_id = Column(UUID(as_uuid=True), ForeignKey("baos.berth.berth_id"))
    berth_code = Column(Text)
    assigned = Column(Boolean, default=True)
    start_ts = Column(DateTime)
    end_ts = Column(DateTime)
    wait_hours = Column(Float)
    service_hours = Column(Float)
    service_time_source = Column(Text)
    cost_usd = Column(Float)
    confidence_score = Column(Float)
    risk_level = Column(Text)
    explanation = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("BaosOptimizationRun", back_populates="assignments")


# ─────────────────────────────────────────────────────────────────────────────
#  Recommendation Log
# ─────────────────────────────────────────────────────────────────────────────

class BaosRecommendationLog(Base):
    __tablename__ = "recommendation_log"
    __table_args__ = {"schema": "baos"}

    recommendation_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("baos.port.port_id"), nullable=False)
    vessel_payload = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    assumptions_used = Column(JSON)
    model_versions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
#  Staging Tables
# ─────────────────────────────────────────────────────────────────────────────

class StgBerthConfigRaw(Base):
    __tablename__ = "stg_berth_config_raw"
    __table_args__ = {"schema": "baos"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_payload = Column(JSON, nullable=False)
    source_file_name = Column(Text)
    source_sheet_name = Column(Text)
    source_row_number = Column(Integer)
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("baos.ingestion_batch.batch_id"))
    source_hash = Column(Text)
    loaded_at = Column(DateTime, default=datetime.utcnow)


class StgBerthCapabilityRaw(Base):
    __tablename__ = "stg_berth_capability_raw"
    __table_args__ = {"schema": "baos"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_payload = Column(JSON, nullable=False)
    source_file_name = Column(Text)
    source_sheet_name = Column(Text)
    source_row_number = Column(Integer)
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("baos.ingestion_batch.batch_id"))
    source_hash = Column(Text)
    loaded_at = Column(DateTime, default=datetime.utcnow)


class StgPortCallRaw(Base):
    __tablename__ = "stg_port_call_raw"
    __table_args__ = {"schema": "baos"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_payload = Column(JSON, nullable=False)
    source_file_name = Column(Text)
    source_sheet_name = Column(Text)
    source_row_number = Column(Integer)
    source_batch_id = Column(UUID(as_uuid=True), ForeignKey("baos.ingestion_batch.batch_id"))
    source_hash = Column(Text)
    loaded_at = Column(DateTime, default=datetime.utcnow)
