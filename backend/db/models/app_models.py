"""
SQLAlchemy ORM models for the BAOS AI platform.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, JSON, Numeric, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


def _uuid():
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────────────────────
#  Users & Sessions
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    company = Column(String(200), default="")
    port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True)
    role = Column(String(30), default="operator")  # admin, operator, view-only
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    port = relationship("Port", back_populates="users", lazy="selectin")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(500), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


# ─────────────────────────────────────────────────────────────────────────────
#  Port & Berth
# ─────────────────────────────────────────────────────────────────────────────

class Port(Base):
    __tablename__ = "ports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String(150), nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    country = Column(String(100), default="India")
    config_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="port")
    berths = relationship("Berth", back_populates="port", cascade="all, delete-orphan")
    kpis = relationship("KPI", back_populates="port", cascade="all, delete-orphan")


class Berth(Base):
    __tablename__ = "berths_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    terminal_code = Column(String(20), default="")
    terminal_name = Column(String(100), default="")
    capacity = Column(Integer, default=1)
    max_loa_m = Column(Float, default=400.0)
    max_beam_m = Column(Float, default=60.0)
    max_draft_m = Column(Float, default=15.0)
    depth_m = Column(Float, default=16.0)
    equipment_types = Column(JSON, default=list)
    allowed_vessel_types = Column(JSON, default=list)
    is_available = Column(Boolean, default=True)
    allow_24x7 = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    port = relationship("Port", back_populates="berths")
    assignments = relationship("Assignment", back_populates="berth")


# ─────────────────────────────────────────────────────────────────────────────
#  Vessel
# ─────────────────────────────────────────────────────────────────────────────

class Vessel(Base):
    __tablename__ = "vessels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String(150), nullable=False)
    vessel_type = Column(String(50), default="")
    loa_m = Column(Float, default=0.0)
    beam_m = Column(Float, default=0.0)
    draft_m = Column(Float, default=0.0)
    dwt = Column(Float, default=0.0)
    cargo_type = Column(String(50), default="")
    cargo_tons = Column(Float, default=0.0)
    imo_number = Column(String(20), default="")
    company = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    assignments = relationship("Assignment", back_populates="vessel")
    recommendations = relationship("Recommendation", back_populates="vessel")


# ─────────────────────────────────────────────────────────────────────────────
#  Assignment (berth allocation)
# ─────────────────────────────────────────────────────────────────────────────

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    vessel_id = Column(UUID(as_uuid=True), ForeignKey("vessels.id"), nullable=False)
    berth_id = Column(UUID(as_uuid=True), ForeignKey("berths_master.id"), nullable=False)
    port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False)
    eta = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    actual_departure = Column(DateTime, nullable=True)
    status = Column(String(30), default="assigned")  # assigned, berthed, departed, cancelled
    turnaround_hours = Column(Float, nullable=True)
    sla_met = Column(Boolean, default=True)
    cost = Column(Numeric(14, 2), default=0)
    revenue = Column(Numeric(14, 2), default=0)
    profit = Column(Numeric(14, 2), default=0)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, default="")

    vessel = relationship("Vessel", back_populates="assignments")
    berth = relationship("Berth", back_populates="assignments")


# ─────────────────────────────────────────────────────────────────────────────
#  Recommendation
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    vessel_id = Column(UUID(as_uuid=True), ForeignKey("vessels.id"), nullable=True)
    berth_code = Column(String(20), nullable=False)
    berth_name = Column(String(100), default="")
    port_code = Column(String(20), default="")
    status = Column(String(30), default="recommended")  # recommended, accepted, rejected
    confidence_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    commercial_score = Column(Float, default=0.0)
    reasoning_json = Column(JSON, default=dict)
    vessel_data_json = Column(JSON, default=dict)  # snapshot of vessel input
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vessel = relationship("Vessel", back_populates="recommendations")


# ─────────────────────────────────────────────────────────────────────────────
#  KPI (daily snapshots)
# ─────────────────────────────────────────────────────────────────────────────

class KPI(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    port_id = Column(UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    vessels_count = Column(Integer, default=0)
    revenue = Column(Numeric(14, 2), default=0)
    cost = Column(Numeric(14, 2), default=0)
    utilization_pct = Column(Float, default=0.0)
    sla_compliance_pct = Column(Float, default=0.0)
    avg_turnaround_hours = Column(Float, default=0.0)
    data_json = Column(JSON, default=dict)  # additional chart data
    created_at = Column(DateTime, default=datetime.utcnow)

    port = relationship("Port", back_populates="kpis")


# ─────────────────────────────────────────────────────────────────────────────
#  Audit Log
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), default="")
    resource_id = Column(String(100), default="")
    changes_json = Column(JSON, default=dict)
    ip_address = Column(String(45), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
