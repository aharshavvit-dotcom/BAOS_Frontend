"""
Canonical Data Models — Single Source of Truth
===============================================
All domain entities with typed fields, data provenance tracking,
and quality scoring. These models replace hardcoded defaults
scattered across the codebase.

Data Source Hierarchy:
  1. Specification (Berth_configurations.xlsx) — highest trust
  2. Operational Capability (Operational_Capability_of_Berth.xlsx)
  3. Historical Inference (port call logs)
  4. Assumption (hardcoded fallback) — lowest trust, flagged RED
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ── Data Provenance ──────────────────────────────────────────────────────────

class DataSource(str, Enum):
    """Where a data value came from — determines trust level."""
    SPEC = "spec"              # From official berth specification sheets
    OPERATIONAL = "operational" # From operational capability records
    HISTORICAL = "historical"  # Inferred from port call history
    ASSUMPTION = "assumption"  # Hardcoded fallback — needs replacement
    USER_INPUT = "user_input"  # Provided by user at runtime

    @property
    def trust_score(self) -> float:
        """Trust level 0-1 for confidence calculations."""
        return {
            DataSource.SPEC: 1.0,
            DataSource.OPERATIONAL: 0.95,
            DataSource.HISTORICAL: 0.75,
            DataSource.ASSUMPTION: 0.4,
            DataSource.USER_INPUT: 0.85,
        }[self]


class QualityGate(str, Enum):
    """Traffic-light quality assessment."""
    GREEN = "green"    # Score > 80: Reliable, from authoritative source
    YELLOW = "yellow"  # Score 60-80: Usable but needs validation
    RED = "red"        # Score < 60: Assumption or missing data — flag it


@dataclass
class ProvenanceField:
    """A value with its data source and quality metadata."""
    value: Any
    source: DataSource = DataSource.ASSUMPTION
    quality: QualityGate = QualityGate.RED
    notes: str = ""

    @classmethod
    def from_spec(cls, value: Any, notes: str = "") -> "ProvenanceField":
        return cls(value=value, source=DataSource.SPEC, quality=QualityGate.GREEN, notes=notes)

    @classmethod
    def from_history(cls, value: Any, notes: str = "") -> "ProvenanceField":
        return cls(value=value, source=DataSource.HISTORICAL, quality=QualityGate.YELLOW, notes=notes)

    @classmethod
    def from_assumption(cls, value: Any, notes: str = "") -> "ProvenanceField":
        return cls(value=value, source=DataSource.ASSUMPTION, quality=QualityGate.RED, notes=notes)

    @classmethod
    def from_operational(cls, value: Any, notes: str = "") -> "ProvenanceField":
        return cls(value=value, source=DataSource.OPERATIONAL, quality=QualityGate.GREEN, notes=notes)


# ── Berth Specification ──────────────────────────────────────────────────────

@dataclass
class BerthSpec:
    """
    Complete berth specification from authoritative sources.
    
    Primary source: Berth_configurations.xlsx (spec sheet)
    Fallback: Historical inference from port call logs
    """
    # Identity
    berth_code: str
    berth_name: str = ""
    terminal_code: str = ""
    terminal_name: str = ""
    terminal_type: str = ""           # Multipurpose, Container, Tanker, Bulk
    port_code: str = ""
    port_name: str = ""

    # Physical limits (Tier 1 — Hard constraints)
    max_loa_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No LOA spec"))
    min_loa_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No min LOA spec"))
    max_draft_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No draft spec"))
    max_depth_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No depth spec"))
    max_beam_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No beam spec"))
    max_dwt: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No DWT spec"))
    max_displacement: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No displacement spec"))
    ukc_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No UKC spec"))

    # Channel constraints
    channel_max_depth_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0))
    channel_max_draft_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0))
    channel_ukc_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0))

    # Air draft
    max_air_draft_m: ProvenanceField = field(default_factory=lambda: ProvenanceField.from_assumption(0.0, "No air draft limit"))

    # Operational attributes
    berthing_side: str = "Either"
    berth_type: str = "Berth"
    seabed_type: str = ""
    water_density: str = ""
    tidal_restricted: bool = False
    shore_gangway: bool = False
    bunkering_allowed: bool = False
    bunkering_during_ops: bool = False
    bunkering_after_ops: bool = False
    allow_24x7: bool = True

    # Operational capability (from Operational_Capability_of_Berth.xlsx)
    supported_operations: List[str] = field(default_factory=list)  # ["Loading", "Discharging"]
    supported_commodities: List[str] = field(default_factory=list)
    commodity_groups: List[str] = field(default_factory=list)
    cargo_categories: Set[str] = field(default_factory=set)        # {"Dry", "Wet"}

    # Vessel type compatibility (derived from operational data + history)
    allowed_vessel_types: List[str] = field(default_factory=list)
    vessel_type_source: DataSource = DataSource.ASSUMPTION

    # Equipment (derived from history or assumed)
    equipment_types: List[str] = field(default_factory=list)
    equipment_source: DataSource = DataSource.ASSUMPTION

    # Historical performance stats
    historical_vessel_count: int = 0
    historical_avg_service_hours: float = 0.0
    historical_max_loa_seen: float = 0.0
    historical_max_draft_seen: float = 0.0

    # Overall quality
    data_quality: QualityGate = QualityGate.RED
    quality_score: float = 0.0  # 0-100

    def get_max_loa(self) -> float:
        """Get the authoritative max LOA value."""
        return float(self.max_loa_m.value) if self.max_loa_m.value else 0.0

    def get_min_loa(self) -> float:
        """Get the minimum LOA requirement (vessel must be at least this long)."""
        return float(self.min_loa_m.value) if self.min_loa_m.value else 0.0

    def get_max_draft(self) -> float:
        """Get the authoritative max draft value."""
        return float(self.max_draft_m.value) if self.max_draft_m.value else 0.0

    def get_depth(self) -> float:
        """Get the authoritative depth value."""
        return float(self.max_depth_m.value) if self.max_depth_m.value else 0.0

    def get_max_beam(self) -> float:
        """Get the authoritative max beam value."""
        v = self.max_beam_m.value
        if v and str(v) != "No Restrictions" and str(v) != "0.0":
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    def get_ukc(self) -> float:
        """Get UKC requirement in meters."""
        v = self.ukc_m.value
        try:
            return float(v) if v else 0.0
        except (ValueError, TypeError):
            return 0.0

    def supports_cargo_category(self, category: str) -> bool:
        """Check if berth can handle Dry or Wet cargo."""
        if not self.cargo_categories:
            return True  # Unknown = allow (but flag)
        return category in self.cargo_categories

    def to_legacy_dict(self) -> dict:
        """Convert to the dict format used by existing port_config.json."""
        return {
            "berth_code": self.berth_code,
            "berth_name": self.berth_name,
            "terminal_code": self.terminal_code,
            "terminal_name": self.terminal_name,
            "port_code": self.port_code,
            "port_name": self.port_name,
            "max_loa_m": self.get_max_loa(),
            "min_loa_m": self.get_min_loa(),
            "max_draft_m": self.get_max_draft(),
            "depth_m": self.get_depth(),
            "max_beam_m": self.get_max_beam(),
            "allowed_vessel_types": self.allowed_vessel_types,
            "equipment": self.equipment_types,
            "allow_24x7": self.allow_24x7,
            # New fields for data quality visibility
            "data_quality": self.data_quality.value,
            "quality_score": self.quality_score,
            "loa_source": self.max_loa_m.source.value,
            "draft_source": self.max_draft_m.source.value,
            "tidal_restricted": self.tidal_restricted,
            "ukc_m": self.get_ukc(),
            "cargo_categories": sorted(self.cargo_categories),
            "supported_commodities": self.supported_commodities[:20],  # Top 20
            "terminal_type": self.terminal_type,
        }


# ── Constraint Definition ────────────────────────────────────────────────────

class ConstraintSeverity(str, Enum):
    """How strictly a constraint must be enforced."""
    HARD = "hard"          # Physical impossibility — cannot be violated
    SOFT_HIGH = "soft_high"  # Strong operational preference — high penalty
    SOFT_LOW = "soft_low"  # Weak preference — low penalty
    INFO = "info"          # Informational only — no penalty


class ConstraintCategory(str, Enum):
    """What type of constraint this is."""
    PHYSICAL = "physical"        # LOA, draft, beam, depth
    OPERATIONAL = "operational"  # Cargo type, equipment, vessel type
    CONTEXTUAL = "contextual"    # Occupancy, weather, tides
    COMMERCIAL = "commercial"    # SLA, contracts, cost


@dataclass
class ConstraintDefinition:
    """A single constraint rule with full metadata."""
    id: str
    name: str
    category: ConstraintCategory
    severity: ConstraintSeverity
    description: str = ""
    source: DataSource = DataSource.ASSUMPTION
    data_quality: QualityGate = QualityGate.RED

    # Rule parameters
    field_name: str = ""        # e.g., "loa", "draft", "cargo_category"
    operator: str = "lte"       # lte, gte, eq, in, not_in
    limit_value: Any = None     # The constraint limit

    # Penalty for soft constraints
    penalty_cost: float = 0.0   # Cost per unit of violation

    def check(self, actual_value: Any) -> "ConstraintCheckResult":
        """Evaluate this constraint against an actual value."""
        passed = True
        margin = 0.0
        reason = ""

        if self.limit_value is None or actual_value is None:
            return ConstraintCheckResult(
                constraint_id=self.id, passed=True,
                reason=f"Skipped: no data for {self.name}",
                data_quality=QualityGate.RED,
            )

        try:
            if self.operator == "lte":
                actual = float(actual_value)
                limit = float(self.limit_value)
                passed = actual <= limit
                margin = limit - actual
                reason = (
                    f"{self.name}: {actual:.1f} {'<=' if passed else '>'} {limit:.1f} "
                    f"(margin: {margin:+.1f})"
                )
            elif self.operator == "gte":
                actual = float(actual_value)
                limit = float(self.limit_value)
                passed = actual >= limit
                margin = actual - limit
                reason = (
                    f"{self.name}: {actual:.1f} {'>=' if passed else '<'} {limit:.1f} "
                    f"(margin: {margin:+.1f})"
                )
            elif self.operator == "in":
                passed = actual_value in self.limit_value
                reason = (
                    f"{self.name}: '{actual_value}' "
                    f"{'found' if passed else 'not found'} in {self.limit_value}"
                )
            elif self.operator == "not_in":
                passed = actual_value not in self.limit_value
                reason = f"{self.name}: '{actual_value}' exclusion check"
            elif self.operator == "eq":
                passed = actual_value == self.limit_value
                reason = f"{self.name}: {actual_value} == {self.limit_value}: {passed}"
        except (ValueError, TypeError) as e:
            passed = True  # Can't check = allow but flag
            reason = f"{self.name}: check failed ({e})"

        return ConstraintCheckResult(
            constraint_id=self.id,
            passed=passed,
            margin=margin,
            reason=reason,
            severity=self.severity,
            source=self.source,
            data_quality=self.data_quality,
        )


@dataclass
class ConstraintCheckResult:
    """Result of evaluating one constraint."""
    constraint_id: str
    passed: bool = True
    margin: float = 0.0           # Positive = within limit, negative = violation
    reason: str = ""
    severity: ConstraintSeverity = ConstraintSeverity.HARD
    source: DataSource = DataSource.ASSUMPTION
    data_quality: QualityGate = QualityGate.RED

    @property
    def is_hard_violation(self) -> bool:
        return not self.passed and self.severity == ConstraintSeverity.HARD

    @property
    def is_soft_violation(self) -> bool:
        return not self.passed and self.severity in (
            ConstraintSeverity.SOFT_HIGH, ConstraintSeverity.SOFT_LOW
        )


@dataclass
class FeasibilityResult:
    """Complete feasibility assessment for a vessel-berth pair."""
    vessel_id: str
    berth_code: str
    feasible: bool = True           # True if no hard constraints violated
    constraint_results: List[ConstraintCheckResult] = field(default_factory=list)
    hard_violations: int = 0
    soft_violations: int = 0
    total_penalty: float = 0.0
    data_quality: QualityGate = QualityGate.RED
    explanation: str = ""

    def add_result(self, result: ConstraintCheckResult):
        self.constraint_results.append(result)
        if result.is_hard_violation:
            self.hard_violations += 1
            self.feasible = False
        elif result.is_soft_violation:
            self.soft_violations += 1

    @property
    def pass_rate(self) -> float:
        """Fraction of constraints that passed."""
        if not self.constraint_results:
            return 0.0
        return sum(1 for r in self.constraint_results if r.passed) / len(self.constraint_results)

    def build_explanation(self) -> str:
        """Build human-readable explanation."""
        parts = []
        if self.feasible:
            parts.append(f"[PASS] Feasible ({self.pass_rate:.0%} constraints pass)")
        else:
            parts.append(f"[FAIL] Infeasible - {self.hard_violations} hard violation(s)")

        for r in self.constraint_results:
            icon = "[OK]" if r.passed else ("[FAIL]" if r.is_hard_violation else "[WARN]")
            parts.append(f"  {icon} {r.reason}")

        self.explanation = "\n".join(parts)
        return self.explanation


# ── Port Master ──────────────────────────────────────────────────────────────

@dataclass
class PortMaster:
    """Complete port entity with all child entities."""
    port_code: str
    port_name: str
    country: str = ""
    unlocode: str = ""
    timezone: str = ""

    # All berth specs
    berths: Dict[str, BerthSpec] = field(default_factory=dict)

    # Overall quality
    data_quality: QualityGate = QualityGate.RED
    quality_score: float = 0.0
    spec_loaded: bool = False
    operational_loaded: bool = False
    history_loaded: bool = False

    def get_berth(self, berth_code: str) -> Optional[BerthSpec]:
        return self.berths.get(str(berth_code))

    def list_berth_codes(self) -> List[str]:
        return sorted(self.berths.keys())

    def summary(self) -> dict:
        """Summary statistics for the port."""
        total = len(self.berths)
        green = sum(1 for b in self.berths.values() if b.data_quality == QualityGate.GREEN)
        yellow = sum(1 for b in self.berths.values() if b.data_quality == QualityGate.YELLOW)
        red = sum(1 for b in self.berths.values() if b.data_quality == QualityGate.RED)
        return {
            "port_name": self.port_name,
            "total_berths": total,
            "quality_green": green,
            "quality_yellow": yellow,
            "quality_red": red,
            "spec_loaded": self.spec_loaded,
            "operational_loaded": self.operational_loaded,
            "history_loaded": self.history_loaded,
        }
