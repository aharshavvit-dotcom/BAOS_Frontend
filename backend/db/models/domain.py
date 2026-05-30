"""
Domain Models for Berth Optimization System
All structured types used across the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid


# ── Enums ────────────────────────────────────────────────────────────────────

class PriorityMode(str, Enum):
    FCFS = "fcfs"
    CONTRACT = "contract"
    PRODUCTIVITY = "productivity"


class VesselStatus(str, Enum):
    QUEUED = "queued"
    CLEARED = "cleared"
    BERTHED = "berthed"
    DEPARTED = "departed"


class ComplianceGate(str, Enum):
    CUSTOMS = "customs"
    FREE_PRATIQUE = "free_pratique"
    IMMIGRATION = "immigration"
    SECURITY = "security"
    PORT_HEALTH = "port_health"


class EquipmentType(str, Enum):
    CRANE = "crane"
    HOSE = "hose"
    GANGWAY = "gangway"
    CONVEYOR = "conveyor"
    RAMP = "ramp"


class ResourceType(str, Enum):
    PILOT = "pilot"
    TUG = "tug"
    CRANE = "crane"
    HOSE = "hose"
    GANGWAY = "gangway"
    MOORING = "mooring"


class DisruptionType(str, Enum):
    LATE_ARRIVAL = "late_arrival"
    EQUIPMENT_BREAKDOWN = "equipment_breakdown"
    WEATHER = "weather"
    TUG_UNAVAILABLE = "tug_unavailable"
    PILOT_UNAVAILABLE = "pilot_unavailable"
    COMPLIANCE_DELAY = "compliance_delay"


class OperationType(str, Enum):
    LOADING = "loading"
    UNLOADING = "unloading"
    BOTH = "both"
    BUNKERING = "bunkering"
    REPAIR = "repair"


class ChannelDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BOTH = "both"


# ── Port infrastructure ─────────────────────────────────────────────────────

@dataclass
class Berth:
    berth_code: str
    berth_name: str
    terminal_code: str
    terminal_name: str
    port_code: str
    port_name: str
    max_loa_m: float = 999.0
    max_beam_m: float = 999.0
    max_draft_m: float = 20.0
    depth_m: float = 15.0
    length_m: float = 300.0
    allowed_vessel_types: List[str] = field(default_factory=list)
    equipment_types: List[str] = field(default_factory=list)
    allow_24x7: bool = True
    work_start: time = time(0, 0)
    work_end: time = time(23, 59)
    shore_storage_capacity_tons: float = 50000.0
    max_parallel_positions: int = 1
    # Navigation / Channel (Phase 0 extension)
    channel_one_way_flag: bool = False
    movement_duration_min: int = 30
    max_simultaneous_movements: int = 2
    # State tracking
    current_occupancy_count: int = 0
    expected_release_time: Optional[datetime] = None


@dataclass
class TideWindow:
    start: datetime
    end: datetime
    height_m: float  # tide height above chart datum
    is_high_tide: bool = False


@dataclass
class WeatherWindow:
    start: datetime
    end: datetime
    wind_speed_knots: float = 0.0
    wave_height_m: float = 0.0
    visibility_nm: float = 10.0
    is_adverse: bool = False
    reason: str = ""


@dataclass
class ChannelWindow:
    start: datetime
    end: datetime
    available: bool = True
    max_simultaneous_movements: int = 1
    reason: str = ""
    direction_restriction: str = "both"  # inbound / outbound / both


# ── Resources ────────────────────────────────────────────────────────────────

@dataclass
class ResourceSlot:
    resource_type: str
    resource_id: str
    available_from: datetime
    available_to: datetime
    capacity: int = 1


@dataclass
class DowntimeWindow:
    resource_type: str
    resource_id: str
    start: datetime
    end: datetime
    reason: str = ""


# ── Vessels & Queue ──────────────────────────────────────────────────────────

@dataclass
class Vessel:
    imo: str = ""
    name: str = ""
    vessel_type: str = ""
    loa_m: float = 0.0
    beam_m: float = 0.0
    draft_m: float = 0.0
    dwt: float = 0.0
    cargo_type: str = ""
    cargo_tons: float = 0.0
    # Commercial (Phase 0 extension)
    demurrage_cost_per_hr: float = 0.0
    cargo_handling_rate_tph: float = 0.0  # tons per hour
    operation_type: str = "both"  # loading / unloading / both / bunkering / repair


@dataclass
class ComplianceStatus:
    gate: str
    cleared: bool = False
    expected_clearance: Optional[datetime] = None
    notes: str = ""


@dataclass
class VesselQueueEntry:
    port_call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vessel: Vessel = field(default_factory=Vessel)
    port_code: str = ""
    terminal_code: str = ""
    berth_code: str = ""  # preferred berth if any
    eta: datetime = field(default_factory=datetime.now)
    service_hours: float = 12.0
    priority: int = 100  # lower = higher priority
    priority_mode: str = PriorityMode.FCFS.value
    goi_override: bool = False
    contract_id: str = ""
    compliance: List[ComplianceStatus] = field(default_factory=list)
    volatility_score: float = 0.0
    status: str = VesselStatus.QUEUED.value
    # Uncertainty & Commercial (Phase 0 extension)
    eta_confidence_score: float = 1.0   # 0..1, 1 = fully confident
    historical_delay_std: float = 0.0   # hours
    sla_wait_limit_hr: float = 24.0
    contract_rank: int = 0              # 0 = no contract


# ── Commercial ───────────────────────────────────────────────────────────────

@dataclass
class ContractRule:
    contract_id: str
    vessel_type: str = ""
    preferred_berths: List[str] = field(default_factory=list)
    priority_boost: int = 0  # negative = higher priority
    sla_max_wait_hours: float = 24.0
    penalty_per_hour_delay: float = 0.0
    min_productivity_tph: float = 0.0


@dataclass
class GoIOverrideRule:
    enabled: bool = False
    force_fcfs: bool = True
    override_contracts: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    reason: str = ""


# ── Optimization artifacts ───────────────────────────────────────────────────

@dataclass
class FeasibilityCheck:
    check_name: str
    passed: bool
    reason: str
    severity: str = "hard"  # hard or soft


@dataclass
class FeasibilityResult:
    vessel_id: str
    berth_code: str
    feasible: bool
    checks: List[FeasibilityCheck] = field(default_factory=list)

    @property
    def reasons(self) -> List[str]:
        return [c.reason for c in self.checks if not c.passed]

    @property
    def reasons_str(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "OK"


@dataclass
class ScheduleEntry:
    port_call_id: str
    vessel_name: str
    vessel_type: str
    imo: str = ""
    loa_m: float = 0.0
    draft_m: float = 0.0
    cargo_type: str = ""
    cargo_tons: float = 0.0
    eta: Optional[datetime] = None
    service_hours: float = 0.0
    priority: int = 100
    assigned_berth: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    waiting_hours: float = 0.0
    status: str = "UNASSIGNED"
    explanation: str = ""


@dataclass
class OptimizationRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_ts: datetime = field(default_factory=datetime.utcnow)
    port_code: str = ""
    engine: str = "greedy"
    settings: Dict[str, Any] = field(default_factory=dict)
    solver_status: str = ""
    objective_value: Optional[float] = None
    solve_time_sec: Optional[float] = None
    schedule: List[ScheduleEntry] = field(default_factory=list)
    feasibility: List[FeasibilityResult] = field(default_factory=list)
    kpis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEntry:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    action: str = ""
    user: str = "system"
    details: str = ""
    run_id: str = ""
    vessel_id: str = ""
    berth_code: str = ""
    before_value: str = ""
    after_value: str = ""


# ── Ship type configuration ─────────────────────────────────────────────────

SHIP_TYPES = ["Container", "Bulk Carrier", "RoRo", "Tanker", "General Cargo"]

CARGO_TYPES = [
    "Bulk Dry", "Liquid Bulk", "Container", "General",
    "Coal", "Iron Ore", "Crude Oil", "Chemicals",
    "LPG/LNG", "Break Bulk",
]

# Intelligent default lever values per ship type.
# Keys match SchedulerConfig weight names so they can be unpacked directly.
SHIP_TYPE_DEFAULTS = {
    "Container": {
        "label": "Container Ships",
        "icon": "📦",
        "description": "High-value cargo, time-sensitive, strict schedules",
        "w_waiting": 2.0,
        "w_sla_penalty": 1.0,
        "w_contract_bonus": 2.0,
        "w_throughput": 1.5,
        "w_deviation": 0.5,
        "w_demurrage": 1.5,
    },
    "Bulk Carrier": {
        "label": "Bulk Carriers",
        "icon": "🏗️",
        "description": "Heavy cargo, equipment-dependent, can wait",
        "w_waiting": 0.5,
        "w_sla_penalty": 1.3,
        "w_contract_bonus": 0.3,
        "w_throughput": 1.0,
        "w_deviation": 0.5,
        "w_demurrage": 0.3,
    },
    "RoRo": {
        "label": "RoRo Vehicles",
        "icon": "🚗",
        "description": "Vehicle carriers, fast loading, quick turnaround",
        "w_waiting": 2.0,
        "w_sla_penalty": 1.5,
        "w_contract_bonus": 0.5,
        "w_throughput": 0.5,
        "w_deviation": 0.5,
        "w_demurrage": 1.0,
    },
    "Tanker": {
        "label": "Tankers",
        "icon": "🛢️",
        "description": "Hazardous cargo, strict safety, time windows",
        "w_waiting": 1.0,
        "w_sla_penalty": 1.0,
        "w_contract_bonus": 0.5,
        "w_throughput": 0.5,
        "w_deviation": 0.8,
        "w_demurrage": 0.5,
    },
    "General Cargo": {
        "label": "General Cargo",
        "icon": "📦",
        "description": "Mixed cargo, flexible, economical",
        "w_waiting": 1.0,
        "w_sla_penalty": 1.0,
        "w_contract_bonus": 0.5,
        "w_throughput": 1.0,
        "w_deviation": 0.5,
        "w_demurrage": 0.5,
    },
}


# ── Lever configuration ─────────────────────────────────────────────────────

@dataclass
class LeverConfig:
    """All tunable levers for the optimizer — directly maps to UI controls."""
    # Priority
    priority_mode: str = PriorityMode.FCFS.value
    goi_override: bool = False

    # Objective weights
    waiting_weight: float = 1.0
    deviation_weight: float = 0.5
    utilization_weight: float = 0.3
    commercial_weight: float = 0.2
    equipment_weight: float = 0.5
    tide_weight: float = 0.3
    size_penalty_weight: float = 0.2
    # BAOS extensions — multi-objective weights
    demurrage_weight: float = 0.5
    stability_weight: float = 0.3
    idle_penalty_weight: float = 0.2
    tide_alignment_weight: float = 0.2

    # Working hours
    allow_24x7: bool = True
    work_start: time = time(0, 0)
    work_end: time = time(23, 59)

    # Constraints
    enforce_tide: bool = True
    enforce_equipment: bool = True
    enforce_compliance: bool = True
    enforce_parallel_movement: bool = True
    enforce_shore_storage: bool = False
    enforce_tug_pilot: bool = True
    # BAOS extensions — new constraint toggles
    enforce_channel: bool = True
    enforce_resources: bool = True

    # Solver
    rolling_horizon_hours: int = 168  # 7 days
    max_solve_seconds: int = 30
    engine: str = "cpsat"

    # Weather buffer
    weather_buffer_hours: float = 2.0
    min_tide_clearance_m: float = 0.5

    # BAOS — Repair engine settings
    repair_freeze_hours: float = 0.0    # freeze assignments older than this
    repair_horizon_hours: float = 12.0  # rolling window for re-optimization

    def to_scheduler_config(self):
        """
        Bridge method: convert LeverConfig weights → SchedulerConfig
        for use in CLI / API / programmatic access.
        """
        from engines.simulation.optimization.constraint_model import SchedulerConfig
        return SchedulerConfig(
            horizon_minutes=self.rolling_horizon_hours * 60,
            max_solve_seconds=self.max_solve_seconds,
            fcfs_enabled=(self.priority_mode == PriorityMode.FCFS.value),
            goi_override_enabled=self.goi_override,
            w_waiting=self.waiting_weight,
            w_sla_penalty=2.0,  # Not in LeverConfig — sensible default
            w_contract_bonus=self.commercial_weight,
            w_throughput=self.utilization_weight,
            w_deviation=self.deviation_weight,
            w_demurrage=self.demurrage_weight,
            ukc_margin_m=self.min_tide_clearance_m,
        )

    def to_dict(self) -> dict:
        return {
            "priority_mode": self.priority_mode,
            "goi_override": self.goi_override,
            "waiting_weight": self.waiting_weight,
            "deviation_weight": self.deviation_weight,
            "utilization_weight": self.utilization_weight,
            "commercial_weight": self.commercial_weight,
            "equipment_weight": self.equipment_weight,
            "tide_weight": self.tide_weight,
            "size_penalty_weight": self.size_penalty_weight,
            "demurrage_weight": self.demurrage_weight,
            "stability_weight": self.stability_weight,
            "idle_penalty_weight": self.idle_penalty_weight,
            "tide_alignment_weight": self.tide_alignment_weight,
            "allow_24x7": self.allow_24x7,
            "work_start": self.work_start.strftime("%H:%M"),
            "work_end": self.work_end.strftime("%H:%M"),
            "enforce_tide": self.enforce_tide,
            "enforce_equipment": self.enforce_equipment,
            "enforce_compliance": self.enforce_compliance,
            "enforce_parallel_movement": self.enforce_parallel_movement,
            "enforce_shore_storage": self.enforce_shore_storage,
            "enforce_tug_pilot": self.enforce_tug_pilot,
            "enforce_channel": self.enforce_channel,
            "enforce_resources": self.enforce_resources,
            "rolling_horizon_hours": self.rolling_horizon_hours,
            "max_solve_seconds": self.max_solve_seconds,
            "engine": self.engine,
            "weather_buffer_hours": self.weather_buffer_hours,
            "min_tide_clearance_m": self.min_tide_clearance_m,
            "repair_freeze_hours": self.repair_freeze_hours,
            "repair_horizon_hours": self.repair_horizon_hours,
        }


# ── Port config (the "configuration package" per port) ──────────────────────

@dataclass
class PortConfig:
    port_code: str
    port_name: str
    berths: List[Berth] = field(default_factory=list)
    tide_windows: List[TideWindow] = field(default_factory=list)
    weather_windows: List[WeatherWindow] = field(default_factory=list)
    channel_windows: List[ChannelWindow] = field(default_factory=list)
    resource_slots: List[ResourceSlot] = field(default_factory=list)
    downtime_windows: List[DowntimeWindow] = field(default_factory=list)
    contract_rules: List[ContractRule] = field(default_factory=list)
    goi_override: GoIOverrideRule = field(default_factory=GoIOverrideRule)
    levers: LeverConfig = field(default_factory=LeverConfig)


# ── Persistence (Phase 9) ────────────────────────────────────────────────────

@dataclass
class PersistenceRecord:
    """Stores planned vs actual data for feedback loop."""
    run_id: str = ""
    port_call_id: str = ""
    vessel_name: str = ""
    planned_berth: str = ""
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_berth: Optional[str] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    operator_override: bool = False
    override_reason: str = ""
    delay_cause: str = ""
    solver_decision_rationale: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
#  COMMERCIAL INTELLIGENCE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class PartnershipTier(str, Enum):
    """Partnership tier for vessel shipping companies."""
    VIP = "VIP"
    PREMIUM = "PREMIUM"
    STANDARD = "STANDARD"
    STRATEGIC_PROSPECT = "STRATEGIC_PROSPECT"


class CommercialDecisionMode(str, Enum):
    """Decision weighting mode for commercial-aware recommendations."""
    TECHNICAL_ONLY       = "technical_only"
    BALANCED             = "balanced"
    REVENUE_FIRST        = "revenue_first"
    PARTNERSHIP_FOCUSED  = "partnership_focused"


@dataclass
class CommercialScore:
    """Commercial scoring breakdown for a single berth-vessel pair."""
    berth_code: str = ""
    # Component scores (0-100 each)
    technical_score: float = 0.0
    commercial_score: float = 0.0
    strategic_score: float = 0.0
    constraint_score: float = 100.0
    # Weighted final score
    final_score: float = 0.0
    # Revenue estimates
    estimated_gross_revenue: float = 0.0
    estimated_net_revenue: float = 0.0
    estimated_profit: float = 0.0
    profit_margin: float = 0.0
    # Partnership
    partnership_tier: str = PartnershipTier.STANDARD.value
    discount_applied_pct: float = 0.0
    dynamic_pricing_multiplier: float = 1.0
    # Context
    decision_mode: str = CommercialDecisionMode.BALANCED.value
    pricing_note: str = ""
    tier_badge: str = "📦 STANDARD"
    commercial_headline: str = ""
    reasons: List[str] = field(default_factory=list)


@dataclass
class CommercialDecisionConfig:
    """Configuration for the commercial decision engine."""
    commercial_flag: bool = False
    partnership_system_enabled: bool = True
    dynamic_pricing_enabled: bool = True
    decision_mode: CommercialDecisionMode = CommercialDecisionMode.BALANCED

    def to_dict(self) -> dict:
        return {
            "commercial_flag": self.commercial_flag,
            "partnership_system_enabled": self.partnership_system_enabled,
            "dynamic_pricing_enabled": self.dynamic_pricing_enabled,
            "decision_mode": self.decision_mode.value,
        }
