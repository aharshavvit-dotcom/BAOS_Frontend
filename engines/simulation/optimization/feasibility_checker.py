"""
Feasibility Checker — Pre-solve constraint validation.

Validates vessel→berth assignments without running the full CP-SAT solver.
Returns a detailed report of which constraints pass/fail for each pair.
Used for:
  - Quick UI feedback before full optimization
  - Explanation of why a berth is/isn't feasible
  - Filtering before ML model inference
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engines.simulation.optimization.constraint_model import (
    VesselInput, BerthInput, TideWindowInput, ResourceInput, SchedulerConfig,
    BerthSchedulerConfig,
)
from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score


@dataclass
class ConstraintCheck:
    """Result of a single constraint check."""
    name: str
    passed: bool
    severity: str = "hard"     # "hard" = must pass, "soft" = advisory
    detail: str = ""
    value: float = 0.0         # actual value checked
    limit: float = 0.0         # constraint limit


@dataclass
class FeasibilityReport:
    """Feasibility report for one (vessel, berth) pair."""
    vessel_id: str
    berth_code: str
    feasible: bool = True
    hard_violations: int = 0
    soft_violations: int = 0
    checks: List[ConstraintCheck] = field(default_factory=list)
    score: float = 1.0   # 0.0 = completely infeasible, 1.0 = fully feasible

    @property
    def violation_summary(self) -> str:
        violations = [c for c in self.checks if not c.passed]
        if not violations:
            return "All constraints satisfied"
        return "; ".join(f"{c.name}: {c.detail}" for c in violations)

    def get_reason_summary(self) -> dict:
        """
        Return structured feasibility summary for UI hover tooltips.

        Returns:
            {'is_feasible': bool, 'reasons': ['LOA OK (margin 50m)', ...]}
        """
        reasons = []
        for check in self.checks:
            if check.passed:
                # Build concise passed-check descriptions
                if check.name == "LOA fit" and check.limit > 0:
                    margin = check.limit - check.value
                    reasons.append(f"LOA OK (margin {margin:.0f}m)")
                elif check.name == "Draft clearance" and check.limit > 0:
                    clearance = check.limit - check.value
                    reasons.append(f"Draft clearance {clearance:.1f}m")
                elif check.name == "Beam fit" and check.limit > 0:
                    reasons.append(f"Beam OK ({check.value:.0f}m / {check.limit:.0f}m)")
                elif check.name == "Vessel type":
                    reasons.append("Cargo compatible")
                elif check.name == "Berth availability":
                    reasons.append("Berth available")
                elif check.name == "24x7 berthing":
                    reasons.append("24x7 operations OK")
                elif check.name == "Customs clearance":
                    reasons.append("Customs cleared")
                elif check.name == "Tide clearance":
                    reasons.append("Tide window available")
                else:
                    reasons.append(f"{check.name} OK")
            else:
                # Build detailed failure descriptions
                if check.name == "LOA fit" and check.value > 0:
                    excess = check.value - check.limit
                    reasons.append(f"LOA exceeds by {excess:.0f}m")
                elif check.name == "Draft clearance" and check.value > 0:
                    excess = check.value - check.limit
                    reasons.append(f"Draft exceeds by {excess:.1f}m")
                elif check.name == "Beam fit" and check.value > 0:
                    excess = check.value - check.limit
                    reasons.append(f"Beam exceeds by {excess:.1f}m")
                elif check.name == "Vessel type":
                    reasons.append("Vessel type incompatible")
                elif check.name == "Cargo type":
                    reasons.append("Cargo type incompatible")
                elif check.name == "Berth availability":
                    reasons.append("Berth unavailable")
                elif check.name == "Night restriction":
                    reasons.append("Night berthing restriction")
                elif check.name == "Customs clearance":
                    reasons.append("Customs not cleared")
                elif check.name == "Tide clearance":
                    reasons.append("No safe tide window")
                else:
                    reasons.append(f"{check.name}: {check.detail}")

        return {"is_feasible": self.feasible, "reasons": reasons}


class FeasibilityChecker:
    """
    Pre-solve feasibility checker.

    Usage:
        checker = FeasibilityChecker(config)
        report  = checker.check(vessel, berth)
        matrix  = checker.check_all(vessels, berths)
    
    When a PortMaster is provided, uses spec-derived constraints from the
    ConstraintLibrary instead of history-derived BerthInput limits.
    """

    def __init__(
        self,
        config=None,  # SchedulerConfig or BerthSchedulerConfig
        tides: Optional[List[TideWindowInput]] = None,
        port_master=None,  # Optional[PortMaster] — enables spec-based constraints
    ):
        # Normalize: extract global config from BerthSchedulerConfig
        if isinstance(config, BerthSchedulerConfig):
            self.config = config.global_config
        else:
            self.config = config or SchedulerConfig()
        self.tides = tides or []
        self.ukc_margin = self.config.ukc_margin_m
        
        # Constraint library from spec sheets (optional)
        self._constraint_lib = None
        self._port_master = port_master
        if port_master is not None:
            try:
                from engines.simulation.optimization.constraint_library import ConstraintLibrary
                self._constraint_lib = ConstraintLibrary(port_master)
            except Exception:
                pass  # Fall back to legacy behavior

    def check(
        self,
        vessel: VesselInput,
        berth: BerthInput,
    ) -> FeasibilityReport:
        """Check all constraints for a single (vessel, berth) pair."""
        report = FeasibilityReport(
            vessel_id=vessel.vessel_id,
            berth_code=berth.berth_code,
        )

        # Physical constraints
        self._check_loa(vessel, berth, report)
        self._check_draft(vessel, berth, report)
        self._check_beam(vessel, berth, report)
        self._check_vessel_type(vessel, berth, report)
        self._check_cargo_type(vessel, berth, report)

        # Temporal constraints
        self._check_berth_availability(vessel, berth, report)
        self._check_night_restriction(vessel, berth, report)

        # Tide constraints
        if self.tides:
            self._check_tide(vessel, berth, report)

        # Policy constraints
        self._check_customs(vessel, report)

        # Compute overall feasibility
        hard_fails = sum(1 for c in report.checks if not c.passed and c.severity == "hard")
        soft_fails = sum(1 for c in report.checks if not c.passed and c.severity == "soft")
        total = len(report.checks) or 1

        report.hard_violations = hard_fails
        report.soft_violations = soft_fails
        report.feasible = (hard_fails == 0)
        report.score = max(0.0, 1.0 - (hard_fails / total) - (soft_fails / total * 0.3))

        return report

    def check_all(
        self,
        vessels: List[VesselInput],
        berths: List[BerthInput],
    ) -> Dict[Tuple[str, str], FeasibilityReport]:
        """Check all (vessel, berth) pairs. Returns {(vid, bc): report}."""
        matrix = {}
        for v in vessels:
            for b in berths:
                matrix[(v.vessel_id, b.berth_code)] = self.check(v, b)
        return matrix

    def get_eligible_berths(
        self,
        vessel: VesselInput,
        berths: List[BerthInput],
    ) -> List[Tuple[BerthInput, FeasibilityReport]]:
        """Return berths that pass all hard constraints, sorted by feasibility score."""
        results = []
        for b in berths:
            report = self.check(vessel, b)
            if report.feasible:
                results.append((b, report))
        return sorted(results, key=lambda x: x[1].score, reverse=True)

    # ── Individual constraint checks ───────────────────────────────────

    def _check_loa(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if v.loa_m <= 0:
            report.checks.append(ConstraintCheck(
                name="LOA fit", passed=True, detail="LOA not specified", severity="soft",
            ))
            return

        # Use spec-derived limit if available, otherwise BerthInput (history-derived)
        max_loa = b.max_loa_m
        source = "history"
        if self._port_master:
            berth_spec = self._port_master.get_berth(b.berth_code)
            if berth_spec and berth_spec.get_max_loa() > 0:
                max_loa = berth_spec.get_max_loa()
                source = berth_spec.max_loa_m.source.value

        passed = v.loa_m <= max_loa
        ratio = v.loa_m / max(max_loa, 1)
        report.checks.append(ConstraintCheck(
            name="LOA fit",
            passed=passed,
            severity="hard",
            detail=f"Vessel LOA {v.loa_m:.0f}m vs berth max {max_loa:.0f}m [{source}] (ratio: {ratio:.2f})"
                   if not passed else
                   f"LOA {v.loa_m:.0f}m fits in {max_loa:.0f}m [{source}] (margin: {max_loa - v.loa_m:.0f}m)",
            value=v.loa_m,
            limit=max_loa,
        ))

    def _check_draft(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if v.draft_m <= 0:
            report.checks.append(ConstraintCheck(
                name="Draft clearance", passed=True, detail="Draft not specified", severity="soft",
            ))
            return

        # Use spec-derived limit if available
        max_draft = b.max_draft_m
        depth = b.depth_m
        ukc = self.ukc_margin
        source = "history"
        if self._port_master:
            berth_spec = self._port_master.get_berth(b.berth_code)
            if berth_spec:
                if berth_spec.get_max_draft() > 0:
                    max_draft = berth_spec.get_max_draft()
                    source = berth_spec.max_draft_m.source.value
                if berth_spec.get_depth() > 0:
                    depth = berth_spec.get_depth()
                if berth_spec.get_ukc() > 0:
                    ukc = berth_spec.get_ukc()

        required_draft = v.draft_m + ukc
        passed = required_draft <= max_draft
        clearance = depth - v.draft_m if depth > 0 else max_draft - v.draft_m
        report.checks.append(ConstraintCheck(
            name="Draft clearance",
            passed=passed,
            severity="hard",
            detail=f"Vessel draft {v.draft_m:.1f}m + UKC {ukc:.1f}m = {required_draft:.1f}m exceeds berth max draft {max_draft:.1f}m [{source}]"
                   if not passed else
                   f"Draft {v.draft_m:.1f}m OK (UKC {ukc:.1f}m), max draft {max_draft:.1f}m [{source}] (clearance: {clearance:.1f}m)",
            value=v.draft_m,
            limit=max_draft,
        ))

    def _check_beam(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if v.beam_m <= 0:
            report.checks.append(ConstraintCheck(
                name="Beam fit", passed=True, detail="Beam not specified", severity="soft",
            ))
            return

        # Use spec-derived limit if available
        max_beam = b.max_beam_m
        source = "history"
        if self._port_master:
            berth_spec = self._port_master.get_berth(b.berth_code)
            if berth_spec and berth_spec.get_max_beam() > 0:
                max_beam = berth_spec.get_max_beam()
                source = berth_spec.max_beam_m.source.value

        passed = v.beam_m <= max_beam
        report.checks.append(ConstraintCheck(
            name="Beam fit",
            passed=passed,
            severity="hard",
            detail=f"Vessel beam {v.beam_m:.1f}m exceeds berth max {max_beam:.1f}m [{source}]"
                   if not passed else
                   f"Beam {v.beam_m:.1f}m fits in {max_beam:.1f}m [{source}]",
            value=v.beam_m,
            limit=max_beam,
        ))

    def _check_vessel_type(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if not v.vessel_type:
            report.checks.append(ConstraintCheck(
                name="Vessel type", passed=True, detail="No vessel type specified", severity="soft",
            ))
            return

        # Dynamic compatibility scoring instead of hard boolean
        compat_score, summary, factors = compute_compatibility_score(
            v.vessel_type, v.cargo_type, b.equipment_types, b.allowed_vessel_types,
        )

        # Score >= 30: feasible (soft warning if < 60)
        # Score < 30: hard-block (dangerous, e.g. tanker without hazmat)
        if compat_score >= 60:
            passed = True
            severity = "soft"
        elif compat_score >= 30:
            passed = True
            severity = "soft"
        else:
            passed = False
            severity = "hard"

        detail_parts = [summary]
        if factors:
            detail_parts.append(" | ".join(factors[:3]))

        report.checks.append(ConstraintCheck(
            name="Vessel type",
            passed=passed,
            severity=severity,
            detail=" — ".join(detail_parts),
            value=compat_score,
            limit=100.0,
        ))

    def _check_berth_availability(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        # Check if vessel ETA + service fits within berth availability
        earliest_end = v.eta_minutes + v.service_time_minutes
        fits = (v.eta_minutes >= b.available_from_min and
                earliest_end <= b.available_to_min)

        report.checks.append(ConstraintCheck(
            name="Berth availability",
            passed=fits,
            severity="hard" if not fits else "soft",
            detail=f"Vessel needs [{v.eta_minutes}-{earliest_end}]min, "
                   f"berth available [{b.available_from_min}-{b.available_to_min}]min",
        ))

    def _check_night_restriction(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if b.allow_24x7:
            report.checks.append(ConstraintCheck(
                name="24x7 berthing", passed=True, detail="Berth allows 24x7 operations",
            ))
            return

        # Check if ETA falls in night hours
        eta_hour = (v.eta_minutes // 60) % 24
        night_start = self.config.night_start_hour
        night_end = self.config.night_end_hour

        is_night = False
        if night_start > night_end:  # e.g., 22:00–06:00
            is_night = eta_hour >= night_start or eta_hour < night_end
        else:
            is_night = night_start <= eta_hour < night_end

        report.checks.append(ConstraintCheck(
            name="Night restriction",
            passed=not is_night,
            severity="soft",  # Vessel can wait for daytime
            detail=f"ETA at hour {eta_hour:02d}:00 is during night hours ({night_start}:00–{night_end}:00)"
                   if is_night else
                   f"ETA at hour {eta_hour:02d}:00 is during operating hours",
        ))

    def _check_tide(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if v.draft_m <= 0:
            return

        # Check if any tide window provides sufficient depth (with UKC margin)
        has_safe_window = False
        best_clearance = -999.0
        required_depth = v.draft_m + self.ukc_margin

        for tw in self.tides:
            effective_depth = b.depth_m + (tw.height_m if tw.is_high_tide else 0)
            clearance = effective_depth - required_depth
            if clearance > best_clearance:
                best_clearance = clearance
            if clearance >= 0 and tw.start_min <= v.eta_minutes + v.service_time_minutes:
                has_safe_window = True

        if not self.tides:
            has_safe_window = True

        report.checks.append(ConstraintCheck(
            name="Tide clearance",
            passed=has_safe_window,
            severity="hard",
            detail=f"Best UKC: {best_clearance:.1f}m (incl. {self.ukc_margin:.1f}m margin) across {len(self.tides)} tide windows"
                   if self.tides else "No tide windows defined",
            value=best_clearance,
        ))

    def _check_customs(self, v: VesselInput, report: FeasibilityReport):
        report.checks.append(ConstraintCheck(
            name="Customs clearance",
            passed=v.customs_cleared,
            severity="hard",
            detail="Vessel cleared for berthing"
                   if v.customs_cleared else
                   "Vessel NOT cleared — customs/immigration pending",
        ))

    def _check_cargo_type(self, v: VesselInput, b: BerthInput, report: FeasibilityReport):
        if not b.allowed_cargo_types or not v.cargo_type:
            report.checks.append(ConstraintCheck(
                name="Cargo type", passed=True, detail="No cargo type restriction", severity="soft",
            ))
            return

        # Check exact match first
        cargo_lower = v.cargo_type.lower().strip()
        exact_match = any(
            cargo_lower == ct.lower().strip() for ct in b.allowed_cargo_types
        )
        # Check fuzzy match (substring)
        fuzzy_match = any(
            cargo_lower in ct.lower() or ct.lower() in cargo_lower
            for ct in b.allowed_cargo_types
        )

        if exact_match:
            passed = True
            severity = "soft"
            detail = f"Cargo '{v.cargo_type}' allowed"
        elif fuzzy_match:
            passed = True
            severity = "soft"
            detail = f"Cargo '{v.cargo_type}' partially matches allowed types: {b.allowed_cargo_types}"
        else:
            # Not in list — soft constraint (can still work, just suboptimal)
            passed = True
            severity = "soft"
            detail = f"Cargo '{v.cargo_type}' not in typical list {b.allowed_cargo_types} — may be feasible with available equipment"

        report.checks.append(ConstraintCheck(
            name="Cargo type",
            passed=passed,
            severity=severity,
            detail=detail,
        ))
