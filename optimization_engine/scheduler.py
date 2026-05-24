"""
Scheduler — Rolling Horizon Multi-Vessel Scheduling.

Orchestrates the full scheduling pipeline:
  1. Accept vessel queue + port state
  2. Convert to CP-SAT input types
  3. Run constraint model
  4. Handle disruptions via repair heuristics
  5. Warm-start from previous solutions
  6. Produce final schedule with KPIs

Phase 4 Enhancements:
  - OptimizationMode: LIVE (re-solve on every change), BATCH, PREVIEW
  - AssignmentChangeEvent: event-driven re-optimization
  - Cost impact feedback on changes
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from optimization_engine.constraint_model import (
    VesselInput, BerthInput, TideWindowInput, ResourceInput,
    SchedulerConfig, BerthConstraintModel, SolverResult,
    AssignmentResult, DowntimeWindowInput, WeatherWindowInput,
    OPTIMAL, FEASIBLE, INFEASIBLE,
)
from optimization_engine.feasibility_checker import (
    FeasibilityChecker, FeasibilityReport,
)


# ── Phase 4: Optimization Modes ─────────────────────────────────────────

class OptimizationMode(Enum):
    """Optimization trigger modes."""
    LIVE = "live"       # Re-solve on every change (< 5s for < 20 vessels)
    BATCH = "batch"     # Re-optimize on schedule (e.g. every 30 min)
    PREVIEW = "preview" # Show impact preview before committing


@dataclass
class AssignmentChangeEvent:
    """Event: user changes a vessel's berth assignment."""
    vessel_id: str
    old_berth_code: str
    new_berth_code: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""


@dataclass
class ChangeImpact:
    """Impact analysis of an assignment change."""
    affected_vessels: List[str] = field(default_factory=list)
    cost_delta: float = 0.0        # positive = more expensive
    wait_delta_minutes: float = 0.0
    feasible: bool = True
    summary: str = ""


@dataclass
class ScheduleSnapshot:
    """A snapshot of the current schedule state."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    solver_result: Optional[SolverResult] = None
    feasibility_matrix: Dict[Tuple[str, str], FeasibilityReport] = field(default_factory=dict)
    frozen_assignments: List[AssignmentResult] = field(default_factory=list)
    run_number: int = 0
    optimization_mode: str = "LIVE"


class RollingHorizonScheduler:
    """
    Multi-vessel scheduler with rolling horizon optimization.

    Features:
      - Full queue optimization via CP-SAT
      - Warm-start from previous solution
      - Frozen assignments (already in progress)
      - Disruption repair with local search
      - Feasibility pre-checking
    """

    def __init__(self, config=None, port_master=None, mode: OptimizationMode = OptimizationMode.LIVE):
        self.config = config or SchedulerConfig()
        self._port_master = port_master
        self._previous_snapshot: Optional[ScheduleSnapshot] = None
        self._run_counter = 0
        self.mode = mode
        self._last_vessels: Optional[List[VesselInput]] = None
        self._last_berths: Optional[List[BerthInput]] = None

    def optimize(
        self,
        vessels: List[VesselInput],
        berths: List[BerthInput],
        tides: Optional[List[TideWindowInput]] = None,
        resources: Optional[List[ResourceInput]] = None,
        frozen_vessel_ids: Optional[List[str]] = None,
        downtimes: Optional[List[DowntimeWindowInput]] = None,
        weather: Optional[List[WeatherWindowInput]] = None,
    ) -> ScheduleSnapshot:
        """
        Run full optimization cycle.

        Args:
            vessels: Vessel queue to schedule.
            berths: Available berths.
            tides: Tide windows (optional).
            resources: Resource pools (optional).
            frozen_vessel_ids: Vessels already berthed (don't re-schedule).

        Returns:
            ScheduleSnapshot with assignments and KPIs.
        """
        self._run_counter += 1

        # Separate frozen vs schedulable vessels
        frozen_ids = set(frozen_vessel_ids or [])
        schedulable = [v for v in vessels if v.vessel_id not in frozen_ids]
        frozen = [v for v in vessels if v.vessel_id in frozen_ids]

        # Pre-check feasibility (with spec-derived limits when available)
        checker = FeasibilityChecker(self.config, tides or [], port_master=self._port_master)
        feas_matrix = checker.check_all(schedulable, berths)

        # Filter out completely infeasible vessels (no eligible berth)
        filtered_vessels = []
        unschedulable = []
        for v in schedulable:
            eligible = any(
                feas_matrix[(v.vessel_id, b.berth_code)].feasible
                for b in berths
            )
            if eligible:
                filtered_vessels.append(v)
            else:
                unschedulable.append(v.vessel_id)

        # Build and solve CP-SAT model
        if filtered_vessels:
            # Pass previous assignments for deviation penalty
            prev_assigns = None
            if self._previous_snapshot and self._previous_snapshot.solver_result:
                prev_assigns = self._previous_snapshot.solver_result.assignments

            model = BerthConstraintModel(
                filtered_vessels, berths, self.config,
                previous_assignments=prev_assigns,
            )

            if tides:
                model.add_tide_constraints(tides)
            if resources:
                model.add_resource_constraints(resources)
            if downtimes:
                model.add_downtime_constraints(downtimes)
            if weather:
                model.add_weather_constraints(weather)

            model.build()

            # Apply warm-start hints from previous solution
            if self._previous_snapshot and self._previous_snapshot.solver_result:
                self._apply_warm_start(model, self._previous_snapshot.solver_result)

            result = model.solve()
        else:
            result = SolverResult(
                status=INFEASIBLE if vessels else OPTIMAL,
                status_name="INFEASIBLE" if vessels else "OPTIMAL",
                unassigned_vessels=unschedulable,
            )

        # Add unschedulable vessels to result
        result.unassigned_vessels.extend(unschedulable)

        # Build snapshot
        snapshot = ScheduleSnapshot(
            solver_result=result,
            feasibility_matrix=feas_matrix,
            frozen_assignments=self._build_frozen_assignments(frozen, berths),
            run_number=self._run_counter,
            optimization_mode=self.mode.value,
        )

        self._previous_snapshot = snapshot
        self._last_vessels = list(vessels)
        self._last_berths = list(berths)
        return snapshot

    def repair_schedule(
        self,
        current_snapshot: ScheduleSnapshot,
        disruption_type: str,
        affected_vessel_id: Optional[str] = None,
        affected_berth_code: Optional[str] = None,
        vessels: Optional[List[VesselInput]] = None,
        berths: Optional[List[BerthInput]] = None,
    ) -> ScheduleSnapshot:
        """
        Repair schedule after a disruption event.

        Disruption types:
          - "late_arrival": vessel arrives later than ETA
          - "equipment_breakdown": berth temporarily unavailable
          - "weather": all berths paused during weather event

        For now: re-runs full optimization with updated inputs.
        Phase 5 will add local search repair heuristics.
        """
        if vessels and berths:
            # Full re-optimization with updated state
            frozen_ids = []
            if current_snapshot.solver_result:
                # Keep vessels already being serviced as frozen
                for a in current_snapshot.solver_result.assignments:
                    if a.vessel_id != affected_vessel_id:
                        frozen_ids.append(a.vessel_id)

            return self.optimize(vessels, berths, frozen_vessel_ids=frozen_ids)
        else:
            return current_snapshot

    def _apply_warm_start(self, model: BerthConstraintModel, prev_result: SolverResult):
        """Seed CP-SAT solver with hints from previous solution."""
        for assignment in prev_result.assignments:
            vid = assignment.vessel_id
            bc = assignment.berth_code

            if vid in model.vessels and bc in model.berths:
                key = (vid, bc)
                if key in model._x:
                    model.model.AddHint(model._x[key], 1)
                if vid in model._start:
                    model.model.AddHint(
                        model._start[vid], assignment.start_minutes
                    )

    def _build_frozen_assignments(
        self,
        frozen_vessels: List[VesselInput],
        berths: List[BerthInput],
    ) -> List[AssignmentResult]:
        """Create placeholder assignments for frozen (in-progress) vessels."""
        frozen = []
        if self._previous_snapshot and self._previous_snapshot.solver_result:
            for a in self._previous_snapshot.solver_result.assignments:
                for v in frozen_vessels:
                    if v.vessel_id == a.vessel_id:
                        frozen.append(a)
                        break
        return frozen

    # ── Phase 4: Event-Driven Methods ─────────────────────────────────

    def handle_assignment_change(
        self,
        event: AssignmentChangeEvent,
        vessels: Optional[List[VesselInput]] = None,
        berths: Optional[List[BerthInput]] = None,
    ) -> ScheduleSnapshot:
        """
        Handle a user-initiated berth change event.

        In LIVE mode: immediately re-optimize with the change constraint.
        In BATCH mode: queue the change for next batch run.
        In PREVIEW mode: return preview_impact instead.
        """
        vlist = vessels or self._last_vessels or []
        blist = berths or self._last_berths or []

        if not vlist or not blist:
            return self._previous_snapshot or ScheduleSnapshot()

        if self.mode == OptimizationMode.PREVIEW:
            # In preview mode, just return impact without committing
            impact = self.preview_impact(event, vlist, blist)
            # Return previous snapshot with impact info attached
            snap = self._previous_snapshot or ScheduleSnapshot()
            if snap.solver_result:
                snap.solver_result.constraint_violations.append(
                    f"PREVIEW: {impact.summary}"
                )
            return snap

        # LIVE or BATCH: Force the vessel to the new berth and re-optimize
        for v in vlist:
            if v.vessel_id == event.vessel_id:
                v.preferred_berths = [event.new_berth_code]
                break

        return self.optimize(vlist, blist)

    def preview_impact(
        self,
        event: AssignmentChangeEvent,
        vessels: Optional[List[VesselInput]] = None,
        berths: Optional[List[BerthInput]] = None,
    ) -> ChangeImpact:
        """
        Estimate cost/schedule impact of a berth change WITHOUT committing.

        Returns ChangeImpact with:
          - affected_vessels: which vessels are displaced
          - cost_delta: estimated cost change in $/hr
          - wait_delta_minutes: change in total wait
          - summary: human-readable description
        """
        vlist = vessels or self._last_vessels or []
        blist = berths or self._last_berths or []

        if not vlist or not blist:
            return ChangeImpact(summary="No data available for impact analysis.")

        # Get baseline KPIs from previous snapshot
        baseline_wait = 0
        if self._previous_snapshot and self._previous_snapshot.solver_result:
            for a in self._previous_snapshot.solver_result.assignments:
                baseline_wait += a.waiting_minutes

        # Simulate the change
        sim_vessels = []
        for v in vlist:
            import copy
            vc = copy.deepcopy(v)
            if vc.vessel_id == event.vessel_id:
                vc.preferred_berths = [event.new_berth_code]
            sim_vessels.append(vc)

        # Run simulation with short timeout
        sim_config = SchedulerConfig(
            horizon_minutes=self.config.horizon_minutes
                if hasattr(self.config, 'horizon_minutes') else 10080,
            max_solve_seconds=5,  # Quick solve for preview
        )
        sim_scheduler = RollingHorizonScheduler(sim_config, self._port_master)
        sim_snap = sim_scheduler.optimize(sim_vessels, blist)

        # Compare
        sim_wait = 0
        affected = []
        if sim_snap.solver_result:
            for a in sim_snap.solver_result.assignments:
                sim_wait += a.waiting_minutes
                # Check if assignment changed from previous
                if self._previous_snapshot and self._previous_snapshot.solver_result:
                    prev_berth = None
                    for pa in self._previous_snapshot.solver_result.assignments:
                        if pa.vessel_id == a.vessel_id:
                            prev_berth = pa.berth_code
                            break
                    if prev_berth and prev_berth != a.berth_code:
                        affected.append(a.vessel_id)

        wait_delta = sim_wait - baseline_wait
        cost_delta = wait_delta / 60 * 500  # Rough: $500/hr demurrage

        n_affected = len(affected)
        summary = (
            f"Moving {event.vessel_id} from {event.old_berth_code} to {event.new_berth_code}: "
            f"{'saves' if cost_delta < 0 else 'costs'} ~${abs(cost_delta):,.0f}, "
            f"affects {n_affected} other vessel{'s' if n_affected != 1 else ''}."
        )

        return ChangeImpact(
            affected_vessels=affected,
            cost_delta=round(cost_delta, 0),
            wait_delta_minutes=wait_delta,
            feasible=sim_snap.solver_result is not None
                and sim_snap.solver_result.status in (OPTIMAL, FEASIBLE),
            summary=summary,
        )
