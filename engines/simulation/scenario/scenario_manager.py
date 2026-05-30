"""
Scenario Manager — Interactive scenario analysis orchestrator.

Core backend for the interactive decision exploration tool.
Orchestrates:
  - Ranked berth alternatives per vessel
  - Manual override injection into the CP-SAT model
  - Impact recalculation (objective delta, cost delta, confidence delta)
  - Move validation with conflict detection

Architecture safety:
  - All overrides pass through the solver (hard constraints never bypassed)
  - Solver remains the single source of truth
  - UI interactions trigger re-solve, never raw schedule mutation
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, fields as dc_fields
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engines.simulation.optimization.constraint_model import (
    VesselInput, BerthInput, SchedulerConfig, ResourceInput,
    TideWindowInput, DowntimeWindowInput, WeatherWindowInput,
    AssignmentResult, SolverResult, BerthConstraintModel,
    build_and_solve, OPTIMAL, FEASIBLE, INFEASIBLE,
)
from engines.simulation.optimization.feasibility_checker import (
    FeasibilityChecker, FeasibilityReport,
)
from engines.analytics.cost.cost_model import CostEngine, CostConfig
from engines.core.decision.confidence import ConfidenceCalculator
from engines.simulation.scenario.conflict_detector import detect_conflicts


# ── Data Structures ────────────────────────────────────────────────────────

@dataclass
class ManualOverride:
    """User override: lock a vessel to a specific berth."""
    vessel_id: str
    berth_code: str
    start_minutes: Optional[int] = None  # None = let solver decide timing


@dataclass
class RankedBerthOption:
    """One berth option for a vessel with full impact metrics."""
    berth_code: str
    berth_name: str
    rank: int
    objective_value: float = 0.0
    waiting_minutes: int = 0
    service_minutes: int = 0
    cost: float = 0.0
    feasibility_reasons: List[str] = field(default_factory=list)
    confidence_pct: float = 0.0
    is_current: bool = False  # True if this is the solver's optimal choice


@dataclass
class ScenarioImpact:
    """Impact comparison between original and modified schedule."""
    original_objective: float = 0.0
    new_objective: float = 0.0
    objective_delta_pct: float = 0.0
    waiting_delta_hours: float = 0.0
    cost_delta: float = 0.0
    cost_delta_pct: float = 0.0
    confidence_original: float = 0.0
    confidence_new: float = 0.0
    confidence_delta: float = 0.0
    conflicts: List[str] = field(default_factory=list)
    sla_risk_change: str = "unchanged"
    summary_lines: List[str] = field(default_factory=list)
    new_result: Optional[SolverResult] = None


# ── Scenario Manager ──────────────────────────────────────────────────────

class ScenarioManager:
    """
    Orchestrates interactive scenario analysis.

    Usage:
        mgr = ScenarioManager(vessels, berths, config)
        ranked = mgr.compute_ranked_alternatives(original_result)
        impact = mgr.apply_overrides([ManualOverride("V1", "B2")], original_result)
    """

    def __init__(
        self,
        vessels: List[VesselInput],
        berths: List[BerthInput],
        config,  # SchedulerConfig or BerthSchedulerConfig
        tides: Optional[List[TideWindowInput]] = None,
        resources: Optional[List[ResourceInput]] = None,
        downtimes: Optional[List[DowntimeWindowInput]] = None,
        weather: Optional[List[WeatherWindowInput]] = None,
    ):
        self.vessels = vessels
        self.vessels_dict = {v.vessel_id: v for v in vessels}
        self.berths = berths
        self.berths_dict = {b.berth_code: b for b in berths}
        self.config = config
        self.tides = tides
        self.resources = resources
        self.downtimes = downtimes
        self.weather = weather

        self._checker = FeasibilityChecker(config, tides or [])
        self._cost_engine = CostEngine()
        self._confidence_calc = ConfidenceCalculator()

    # ── Ranked Alternatives ────────────────────────────────────────────

    def compute_ranked_alternatives(
        self,
        original_result: SolverResult,
        top_k: int = 5,
    ) -> Dict[str, List[RankedBerthOption]]:
        """
        For each vessel, compute ranked berth alternatives with metrics.

        Uses the feasibility checker for pre-filtering, then runs the solver
        with each vessel locked to each feasible berth to get accurate
        objective values.
        """
        alternatives: Dict[str, List[RankedBerthOption]] = {}

        # Build current assignment map
        current_map = {}
        if original_result and original_result.assignments:
            current_map = {
                a.vessel_id: a for a in original_result.assignments
            }

        for vessel in self.vessels:
            vid = vessel.vessel_id

            # Get eligible berths via feasibility checker
            eligible = self._checker.get_eligible_berths(vessel, self.berths)
            if not eligible:
                alternatives[vid] = []
                continue

            options: List[RankedBerthOption] = []
            current_assignment = current_map.get(vid)

            for berth, feas_report in eligible[:top_k]:
                # Get reason summary
                reasons = []
                for check in feas_report.checks:
                    if check.passed:
                        reasons.append(f"{check.name}: {check.detail}")

                # Determine if this is the current assignment
                is_current = (
                    current_assignment is not None
                    and current_assignment.berth_code == berth.berth_code
                )

                # Use current assignment metrics if available
                if is_current and current_assignment:
                    wait_min = current_assignment.waiting_minutes
                    svc_min = current_assignment.service_minutes
                    obj_val = original_result.objective_value
                else:
                    # Estimate from solving with this vessel locked
                    locked_result = self._solve_with_lock(vid, berth.berth_code)
                    if locked_result and locked_result.status in (OPTIMAL, FEASIBLE):
                        locked_assign = next(
                            (a for a in locked_result.assignments if a.vessel_id == vid),
                            None,
                        )
                        wait_min = locked_assign.waiting_minutes if locked_assign else 0
                        svc_min = locked_assign.service_minutes if locked_assign else vessel.service_time_minutes
                        obj_val = locked_result.objective_value
                    else:
                        wait_min = 0
                        svc_min = vessel.service_time_minutes
                        obj_val = float('inf')

                # Compute cost for this option
                cost_bd = self._cost_engine.compute_vessel_cost(
                    wait_hours=wait_min / 60,
                    service_hours=svc_min / 60,
                    cargo_tons=vessel.cargo_tons,
                    demurrage_rate=vessel.demurrage_cost_per_hr,
                    sla_max_wait_hours=vessel.sla_max_wait_minutes / 60,
                )

                # Compute confidence
                conf = self._confidence_calc.compute(
                    feasibility_checks=feas_report.checks,
                    solver_status=original_result.status if is_current else (
                        locked_result.status if locked_result else None
                    ),
                )

                options.append(RankedBerthOption(
                    berth_code=berth.berth_code,
                    berth_name=berth.berth_name,
                    rank=0,  # Will be set after sorting
                    objective_value=obj_val,
                    waiting_minutes=wait_min,
                    service_minutes=svc_min,
                    cost=cost_bd.total_cost,
                    feasibility_reasons=reasons,
                    confidence_pct=conf.confidence_pct,
                    is_current=is_current,
                ))

            # Sort by objective value (lower is better), then assign ranks
            options.sort(key=lambda o: (not o.is_current, o.objective_value))
            for i, opt in enumerate(options):
                opt.rank = i + 1

            alternatives[vid] = options

        return alternatives

    # ── Override Application ───────────────────────────────────────────

    def apply_overrides(
        self,
        overrides: List[ManualOverride],
        original_result: SolverResult,
    ) -> ScenarioImpact:
        """
        Apply manual overrides and re-solve the schedule.

        Injects lock constraints (x[v, b] = 1) for each override,
        then re-runs the full solver. Returns impact comparison.
        """
        impact = ScenarioImpact()

        if not overrides:
            impact.summary_lines = ["No overrides applied"]
            return impact

        # Validate overrides first
        all_conflicts = []
        for ov in overrides:
            if ov.vessel_id not in self.vessels_dict:
                all_conflicts.append(f"Unknown vessel: {ov.vessel_id}")
                continue
            if ov.berth_code not in self.berths_dict:
                all_conflicts.append(f"Unknown berth: {ov.berth_code}")
                continue

            # Quick feasibility check
            v = self.vessels_dict[ov.vessel_id]
            b = self.berths_dict[ov.berth_code]
            report = self._checker.check(v, b)
            if not report.feasible:
                all_conflicts.append(
                    f"{v.name or ov.vessel_id} -> {ov.berth_code}: "
                    f"{report.violation_summary}"
                )

        if all_conflicts:
            impact.conflicts = all_conflicts
            impact.summary_lines = [
                f"⚠ {len(all_conflicts)} conflict(s) detected — override rejected"
            ] + all_conflicts
            return impact

        # Re-solve with overrides
        override_pairs = [(ov.vessel_id, ov.berth_code) for ov in overrides]
        new_result = self._solve_with_overrides(override_pairs)

        if not new_result or new_result.status not in (OPTIMAL, FEASIBLE):
            impact.conflicts = ["Solver could not find a feasible solution with overrides"]
            impact.summary_lines = ["❌ Infeasible — overrides conflict with hard constraints"]
            return impact

        impact.new_result = new_result

        # ── Compute deltas ──────────────────────────────────────────────
        orig_obj = original_result.objective_value
        new_obj = new_result.objective_value
        impact.original_objective = orig_obj
        impact.new_objective = new_obj
        impact.objective_delta_pct = (
            ((new_obj - orig_obj) / max(abs(orig_obj), 1)) * 100
        )

        # Waiting time delta
        orig_wait = sum(a.waiting_minutes for a in original_result.assignments) / 60
        new_wait = sum(a.waiting_minutes for a in new_result.assignments) / 60
        impact.waiting_delta_hours = new_wait - orig_wait

        # Cost delta
        vessels_dict = self.vessels_dict
        berths_dict = self.berths_dict

        orig_cost = self._cost_engine.compute_schedule_cost(
            original_result.assignments, vessels_dict, berths_dict,
        )
        new_cost = self._cost_engine.compute_schedule_cost(
            new_result.assignments, vessels_dict, berths_dict,
        )

        impact.cost_delta = new_cost.total_cost - orig_cost.total_cost
        impact.cost_delta_pct = (
            (impact.cost_delta / max(orig_cost.total_cost, 1)) * 100
        )

        # Confidence delta (average across vessels)
        def _avg_confidence(result: SolverResult) -> float:
            if not result.assignments:
                return 0.0
            total = 0.0
            for a in result.assignments:
                v = vessels_dict.get(a.vessel_id)
                b = berths_dict.get(a.berth_code)
                if v and b:
                    report = self._checker.check(v, b)
                    conf = self._confidence_calc.compute(
                        feasibility_checks=report.checks,
                        solver_status=result.status,
                    )
                    total += conf.confidence_pct
            return total / len(result.assignments)

        impact.confidence_original = _avg_confidence(original_result)
        impact.confidence_new = _avg_confidence(new_result)
        impact.confidence_delta = impact.confidence_new - impact.confidence_original

        # SLA risk change
        orig_sla_violations = sum(
            1 for a in original_result.assignments if a.sla_exceeded
        )
        new_sla_violations = sum(
            1 for a in new_result.assignments if a.sla_exceeded
        )
        if new_sla_violations > orig_sla_violations:
            impact.sla_risk_change = "increased"
        elif new_sla_violations < orig_sla_violations:
            impact.sla_risk_change = "improved"
        else:
            impact.sla_risk_change = "unchanged"

        # Build summary lines
        lines = []
        if abs(impact.waiting_delta_hours) > 0.1:
            sign = "+" if impact.waiting_delta_hours > 0 else ""
            lines.append(f"{sign}{impact.waiting_delta_hours:.1f}h waiting time")

        if abs(impact.cost_delta_pct) > 0.1:
            sign = "+" if impact.cost_delta_pct > 0 else ""
            lines.append(f"{sign}{impact.cost_delta_pct:.1f}% cost change (${impact.cost_delta:+,.0f})")

        if abs(impact.confidence_delta) > 1:
            sign = "+" if impact.confidence_delta > 0 else ""
            lines.append(f"{sign}{impact.confidence_delta:.1f}% confidence")

        if impact.sla_risk_change != "unchanged":
            lines.append(f"SLA risk {impact.sla_risk_change}")

        impact.summary_lines = lines if lines else ["Schedule unchanged"]

        return impact

    # ── Move Validation ────────────────────────────────────────────────

    def validate_move(
        self,
        vessel_id: str,
        new_berth: str,
        new_start_minutes: int,
        existing_assignments: List[AssignmentResult],
    ) -> Tuple[bool, List[str]]:
        """
        Validate a proposed vessel move (from drag-drop or manual entry).

        Returns (is_valid, conflict_messages).
        """
        vessel = self.vessels_dict.get(vessel_id)
        if not vessel:
            return False, [f"Unknown vessel: {vessel_id}"]

        end_min = new_start_minutes + vessel.service_time_minutes

        conflicts = detect_conflicts(
            vessel_id=vessel_id,
            berth_code=new_berth,
            start_min=new_start_minutes,
            end_min=end_min,
            vessels=self.vessels_dict,
            berths=self.berths_dict,
            existing_assignments=existing_assignments,
            resources=self.resources,
            downtimes=self.downtimes,
            config=self.config,
        )

        return len(conflicts) == 0, conflicts

    # ── Private Solver Helpers ─────────────────────────────────────────

    def _solve_with_lock(
        self, vessel_id: str, berth_code: str,
    ) -> Optional[SolverResult]:
        """Solve with one vessel locked to a specific berth."""
        try:
            model = BerthConstraintModel(
                self.vessels, self.berths, self.config,
            )
            if self.tides:
                model.add_tide_constraints(self.tides)
            if self.resources:
                model.add_resource_constraints(self.resources)
            if self.downtimes:
                model.add_downtime_constraints(self.downtimes)
            if self.weather:
                model.add_weather_constraints(self.weather)

            # Lock the assignment
            model.add_manual_overrides([(vessel_id, berth_code)])
            model.build()

            # Use shorter solve time for alternatives
            max_time = min(self.config.max_solve_seconds, 10)
            model.model.Proto().parameters.max_time_in_seconds = max_time

            return model.solve()
        except Exception:
            return None

    def _solve_with_overrides(
        self, overrides: List[Tuple[str, str]],
    ) -> Optional[SolverResult]:
        """Solve with multiple vessel→berth locks."""
        try:
            model = BerthConstraintModel(
                self.vessels, self.berths, self.config,
            )
            if self.tides:
                model.add_tide_constraints(self.tides)
            if self.resources:
                model.add_resource_constraints(self.resources)
            if self.downtimes:
                model.add_downtime_constraints(self.downtimes)
            if self.weather:
                model.add_weather_constraints(self.weather)

            # Lock all overrides
            model.add_manual_overrides(overrides)
            model.build()

            return model.solve()
        except Exception:
            return None
