"""
Constraint Model — CP-SAT formulation for berth scheduling.

Decision variables:
    X[v, b]  = BoolVar — vessel v assigned to berth b
    start[v] = IntVar  — start time (minutes from epoch) for vessel v
    end[v]   = IntVar  — end time for vessel v
    interval[v, b] = OptionalIntervalVar — occupation interval

Hard constraints implemented:
    C1  LOA fit              vessel.loa <= berth.max_loa
    C2  Draft clearance      vessel.draft <= berth.depth - tide_correction
    C3  Beam fit             vessel.beam <= berth.max_beam
    C4  One vessel per berth Non-overlapping intervals per berth
    C5  Berth availability   Assignment only within berth windows
    C6  Tide window          Berthing restricted to safe tide periods
    C7  24x7 flag            Night restriction unless berth allows 24x7
    C8  Tug availability     Tug count not exceeded per time slot
    C9  Pilot availability   Pilot count not exceeded per time slot
    C10 Channel constraint   Max simultaneous movements
    C11 Customs clearance    Vessel must be cleared before berthing
    C12 FCFS ordering        If enabled, ETA order is respected
    C13 GoI override         Government priority vessels forced first
    C14 Contract preference  Preferred berth bonus (soft constraint)
    C15 SLA commitment       Soft penalty for exceeding SLA wait limit
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score


# ── Solver result codes ────────────────────────────────────────────────────
OPTIMAL = cp_model.OPTIMAL
FEASIBLE = cp_model.FEASIBLE
INFEASIBLE = cp_model.INFEASIBLE
MODEL_INVALID = cp_model.MODEL_INVALID


# ── Input data containers ──────────────────────────────────────────────────

@dataclass
class VesselInput:
    """Vessel to be scheduled."""
    vessel_id: str
    name: str = ""
    vessel_type: str = ""
    loa_m: float = 0.0
    beam_m: float = 0.0
    draft_m: float = 0.0
    dwt: float = 0.0
    cargo_type: str = ""
    cargo_tons: float = 0.0
    eta_minutes: int = 0            # minutes from horizon start
    service_time_minutes: int = 720  # predicted service time
    priority: int = 100              # lower = higher priority
    contract_rank: int = 0           # 0 = no contract
    preferred_berths: List[str] = field(default_factory=list)
    sla_max_wait_minutes: int = 1440  # 24h default
    demurrage_cost_per_hr: float = 0.0
    needs_tug: bool = True
    needs_pilot: bool = True
    customs_cleared: bool = True
    government_priority: bool = False


@dataclass
class BerthInput:
    """Berth slot to assign vessels into."""
    berth_code: str
    berth_name: str = ""
    max_loa_m: float = 999.0
    max_beam_m: float = 999.0
    max_draft_m: float = 20.0
    depth_m: float = 15.0
    allowed_vessel_types: List[str] = field(default_factory=list)
    allowed_cargo_types: List[str] = field(default_factory=list)
    equipment_types: List[str] = field(default_factory=list)
    allow_24x7: bool = True
    available_from_min: int = 0       # minutes from horizon start
    available_to_min: int = 10080     # 7 days default
    channel_one_way: bool = False


@dataclass
class TideWindowInput:
    """Safe tide window for vessel movements."""
    start_min: int
    end_min: int
    height_m: float
    is_high_tide: bool = False


@dataclass
class DowntimeWindowInput:
    """Planned downtime window for a berth."""
    berth_code: str
    start_min: int
    end_min: int
    reason: str = ""


@dataclass
class WeatherWindowInput:
    """Adverse weather window — blocks ALL berths."""
    start_min: int
    end_min: int
    reason: str = ""


@dataclass
class ResourceInput:
    """Shared resource pool (tugs, pilots, cranes)."""
    resource_type: str           # "tug", "pilot", "crane"
    capacity: int = 2            # max concurrent users
    # Time-varying availability: list of (start_min, end_min, capacity)
    schedule: List[Tuple[int, int, int]] = field(default_factory=list)


@dataclass
class SchedulerConfig:
    """Configuration knobs for the optimizer."""
    horizon_minutes: int = 10080       # 7 days
    time_slot_minutes: int = 30        # granularity
    max_solve_seconds: int = 30
    fcfs_enabled: bool = False
    goi_override_enabled: bool = False
    # Objective weights
    w_waiting: float = 1.0
    w_idle: float = 0.3
    w_sla_penalty: float = 2.0
    w_contract_bonus: float = 0.5
    w_throughput: float = 0.5
    w_deviation: float = 0.5           # penalty for schedule instability
    w_demurrage: float = 0.0           # per-vessel demurrage weight (0=off)
    # Commercial Intelligence weights (NEW)
    w_commercial: float = 0.0          # revenue loss weight (0=off)
    w_partnership: float = 0.0         # partnership satisfaction weight (0=off)
    decision_mode: str = "technical_only"  # balanced/revenue_first/partnership_focused
    # Safety margins
    ukc_margin_m: float = 0.5          # under-keel clearance margin
    # Night hours (if berth not 24x7)
    night_start_hour: int = 22
    night_end_hour: int = 6
    # Channel
    max_channel_movements: int = 2
    movement_duration_minutes: int = 60


@dataclass
class BerthSchedulerConfig:
    """Multi-dimensional optimizer configuration.

    Supports four levels of configuration granularity:
      1. Global — one config for all berths and ship types
      2. Per-berth — berth-specific configs
      3. Per-ship-type — ship-type-specific configs (all berths)
      4. Per-berth + per-ship-type — most granular

    Lookup priority (most specific wins):
      for_berth_and_type(berth, ship_type):
        (berth, ship_type) → ship_type only → berth only → global
    """
    global_config: SchedulerConfig = field(default_factory=SchedulerConfig)
    berth_configs: Dict[str, SchedulerConfig] = field(default_factory=dict)
    # Ship-type configs: applies to ALL berths for this ship type
    ship_type_configs: Dict[str, SchedulerConfig] = field(default_factory=dict)
    # Berth + ship-type configs: most granular (berth_code, ship_type) → config
    berth_ship_configs: Dict[Tuple[str, str], SchedulerConfig] = field(default_factory=dict)

    def for_berth(self, berth_code: str) -> SchedulerConfig:
        """Return berth-specific config, falling back to global."""
        return self.berth_configs.get(berth_code, self.global_config)

    def for_berth_and_type(self, berth_code: str, ship_type: str) -> SchedulerConfig:
        """Return config with 4-level priority lookup.

        Priority: (berth, ship_type) → ship_type only → berth only → global.
        """
        # Most specific: berth + ship_type
        key = (berth_code, ship_type)
        if key in self.berth_ship_configs:
            return self.berth_ship_configs[key]
        # Ship-type global (all berths)
        if ship_type and ship_type in self.ship_type_configs:
            return self.ship_type_configs[ship_type]
        # Berth only
        return self.for_berth(berth_code)

    @property
    def max_solve_seconds_effective(self) -> int:
        """Use the maximum solve time across all configs."""
        times = [self.global_config.max_solve_seconds]
        for bc_cfg in self.berth_configs.values():
            times.append(bc_cfg.max_solve_seconds)
        for st_cfg in self.ship_type_configs.values():
            times.append(st_cfg.max_solve_seconds)
        for bst_cfg in self.berth_ship_configs.values():
            times.append(bst_cfg.max_solve_seconds)
        return max(times)

    @property
    def is_per_berth(self) -> bool:
        return len(self.berth_configs) > 0 or len(self.berth_ship_configs) > 0

    @property
    def has_ship_type_configs(self) -> bool:
        return len(self.ship_type_configs) > 0 or len(self.berth_ship_configs) > 0

    @staticmethod
    def wrap(config) -> "BerthSchedulerConfig":
        """Accept SchedulerConfig or BerthSchedulerConfig; always return BSC."""
        if isinstance(config, BerthSchedulerConfig):
            return config
        return BerthSchedulerConfig(global_config=config, berth_configs={})


@dataclass
class AssignmentResult:
    """Output: one vessel→berth assignment."""
    vessel_id: str
    vessel_name: str
    berth_code: str
    berth_name: str
    start_minutes: int
    end_minutes: int
    waiting_minutes: int
    service_minutes: int
    sla_exceeded: bool = False
    sla_excess_minutes: int = 0
    is_preferred_berth: bool = False
    explanation: str = ""


@dataclass
class SolverResult:
    """Full solver output."""
    status: int                          # OPTIMAL / FEASIBLE / INFEASIBLE
    status_name: str = ""
    solve_time_sec: float = 0.0
    objective_value: float = 0.0
    assignments: List[AssignmentResult] = field(default_factory=list)
    unassigned_vessels: List[str] = field(default_factory=list)
    constraint_violations: List[str] = field(default_factory=list)
    kpis: Dict[str, float] = field(default_factory=dict)
    ranked_alternatives: Dict[str, list] = field(default_factory=dict)


# ── CP-SAT Model Builder ──────────────────────────────────────────────────

class BerthConstraintModel:
    """
    Build and solve a CP-SAT model for multi-vessel berth scheduling.
    
    Usage:
        model = BerthConstraintModel(vessels, berths, config)
        model.add_tide_windows(tides)
        model.add_resources(resources)
        result = model.solve()
    """

    def __init__(
        self,
        vessels: List[VesselInput],
        berths: List[BerthInput],
        config,  # SchedulerConfig or BerthSchedulerConfig
        previous_assignments: Optional[List[AssignmentResult]] = None,
    ):
        self.vessels = {v.vessel_id: v for v in vessels}
        self.berths = {b.berth_code: b for b in berths}
        # Wrap into BerthSchedulerConfig for uniform access
        self.berth_config = BerthSchedulerConfig.wrap(config)
        # Keep self.config pointing to global for backward compat
        self.config = self.berth_config.global_config
        self.tides: List[TideWindowInput] = []
        self.resources: List[ResourceInput] = []
        self.previous_assignments = previous_assignments or []

        self.model = cp_model.CpModel()

        # Decision variables
        self._x: Dict[Tuple[str, str], Any] = {}        # X[v,b] = BoolVar
        self._start: Dict[str, Any] = {}                 # start[v] IntVar
        self._end: Dict[str, Any] = {}                   # end[v] IntVar
        self._intervals: Dict[Tuple[str, str], Any] = {} # interval[v,b]
        self._waiting: Dict[str, Any] = {}               # waiting[v] IntVar

        self._build_variables()

    # ── Variable Creation ──────────────────────────────────────────────

    def _build_variables(self):
        """Create decision variables for every feasible (vessel, berth) pair."""
        H = self.config.horizon_minutes

        for vid, v in self.vessels.items():
            # Start time: vessel can start from ETA to horizon end
            self._start[vid] = self.model.NewIntVar(
                v.eta_minutes, H, f"start_{vid}"
            )
            # End time
            self._end[vid] = self.model.NewIntVar(
                v.eta_minutes + v.service_time_minutes, H + v.service_time_minutes,
                f"end_{vid}"
            )
            # End = start + service_time
            self.model.Add(
                self._end[vid] == self._start[vid] + v.service_time_minutes
            )

            # Waiting = start - eta (≥ 0)
            self._waiting[vid] = self.model.NewIntVar(0, H, f"wait_{vid}")
            self.model.Add(
                self._waiting[vid] == self._start[vid] - v.eta_minutes
            )

            for bc, b in self.berths.items():
                # Assignment boolean
                self._x[vid, bc] = self.model.NewBoolVar(f"x_{vid}_{bc}")

                # Optional interval (active only if x[v,b] = 1)
                self._intervals[vid, bc] = self.model.NewOptionalIntervalVar(
                    self._start[vid],
                    v.service_time_minutes,
                    self._end[vid],
                    self._x[vid, bc],
                    f"interval_{vid}_{bc}",
                )

            # Each vessel assigned to exactly one berth
            berth_bools = [self._x[vid, bc] for bc in self.berths]
            self.model.AddExactlyOne(berth_bools)

    # ── Physical Constraints (C1–C3) ───────────────────────────────────

    def add_physical_constraints(self):
        """
        C1: LOA fit — vessel.loa ≤ berth.max_loa
        C2: Draft clearance — vessel.draft ≤ berth.max_draft (tide-adjusted in add_tide_constraints)
        C3: Beam fit — vessel.beam ≤ berth.max_beam

        Uses per-berth UKC safety margin from BerthSchedulerConfig.
        """
        for vid, v in self.vessels.items():
            for bc, b in self.berths.items():
                # Per-berth UKC margin
                berth_cfg = self.berth_config.for_berth(bc)
                ukc = berth_cfg.ukc_margin_m
                infeasible = False

                # C1: LOA
                if v.loa_m > 0 and b.max_loa_m < v.loa_m:
                    infeasible = True

                # C2: Static draft check with UKC safety margin
                if v.draft_m > 0 and b.max_draft_m < (v.draft_m + ukc):
                    infeasible = True

                # C3: Beam
                if v.beam_m > 0 and b.max_beam_m < v.beam_m:
                    infeasible = True

                # Vessel type + cargo type: dynamic compatibility scoring
                # instead of hard boolean rejection
                if v.vessel_type:
                    compat_score, _, _ = compute_compatibility_score(
                        v.vessel_type, v.cargo_type,
                        b.equipment_types, b.allowed_vessel_types,
                    )
                    if compat_score < 30:
                        # Truly dangerous combination — hard block
                        infeasible = True
                    elif compat_score < 60:
                        # Marginal — add penalty to objective (handled in _build_objective)
                        pass  # Solver will add compatibility penalty
                    # else: good/excellent match — no penalty

                if infeasible:
                    self.model.Add(self._x[vid, bc] == 0)

    # ── Temporal Constraints (C4–C7) ───────────────────────────────────

    def add_temporal_constraints(self):
        """
        C4: One vessel per berth at any time — non-overlapping intervals.
        C5: Berth availability window.
        C6: Tide windows (delegated to add_tide_constraints).
        C7: 24x7 flag — restrict night berthing if not allowed.
        """
        # C4: Non-overlapping intervals per berth
        for bc in self.berths:
            berth_intervals = [
                self._intervals[vid, bc] for vid in self.vessels
            ]
            if berth_intervals:
                self.model.AddNoOverlap(berth_intervals)

        # C5: Berth availability — vessel must start and end within berth window
        for vid, v in self.vessels.items():
            for bc, b in self.berths.items():
                # If assigned to this berth, start must be >= berth available_from
                self.model.Add(
                    self._start[vid] >= b.available_from_min
                ).OnlyEnforceIf(self._x[vid, bc])
                # End must be <= berth available_to
                self.model.Add(
                    self._end[vid] <= b.available_to_min
                ).OnlyEnforceIf(self._x[vid, bc])

        # C7: Night restriction for non-24x7 berths
        slot = self.config.time_slot_minutes
        if slot > 0:
            for vid in self.vessels:
                for bc, b in self.berths.items():
                    if not b.allow_24x7:
                        self._add_night_restriction(vid, bc)

    def _add_night_restriction(self, vid: str, bc: str):
        """Prevent berthing start during night hours for non-24x7 berths."""
        cfg = self.config
        # Convert night hours to minute-of-day
        night_start = cfg.night_start_hour * 60
        night_end = cfg.night_end_hour * 60

        # Create a helper variable: minute_of_day for start time
        # start_mod = start[v] mod (24*60)
        day_minutes = 24 * 60
        start_mod = self.model.NewIntVar(0, day_minutes - 1, f"start_mod_{vid}_{bc}")
        # We need: start_mod = start[v] % day_minutes
        quotient = self.model.NewIntVar(0, self.config.horizon_minutes // day_minutes + 1,
                                         f"quot_{vid}_{bc}")
        self.model.Add(
            self._start[vid] == quotient * day_minutes + start_mod
        )

        # Night = [night_start, day_minutes) ∪ [0, night_end)
        # We forbid start_mod in these ranges when assigned to this berth
        if night_start < day_minutes:
            # is_night1: start_mod >= night_start
            is_night1 = self.model.NewBoolVar(f"night1_{vid}_{bc}")
            self.model.Add(start_mod >= night_start).OnlyEnforceIf(is_night1)
            self.model.Add(start_mod < night_start).OnlyEnforceIf(is_night1.Not())

            # is_night2: start_mod < night_end
            is_night2 = self.model.NewBoolVar(f"night2_{vid}_{bc}")
            self.model.Add(start_mod < night_end).OnlyEnforceIf(is_night2)
            self.model.Add(start_mod >= night_end).OnlyEnforceIf(is_night2.Not())

            # If assigned to this berth, must NOT be in night period
            # night = is_night1 OR is_night2
            is_night = self.model.NewBoolVar(f"night_{vid}_{bc}")
            self.model.AddMaxEquality(is_night, [is_night1, is_night2])

            # If x[v,b]=1 → is_night = 0
            self.model.Add(is_night == 0).OnlyEnforceIf(self._x[vid, bc])

    # ── Tide Constraints (C6) ──────────────────────────────────────────

    def add_tide_constraints(self, tides: List[TideWindowInput]):
        """
        C6: Vessel must start berthing during a safe tide window
        where tide_height gives sufficient depth for vessel draft + UKC margin.
        """
        self.tides = tides
        if not tides:
            return

        ukc = self.config.ukc_margin_m
        for vid, v in self.vessels.items():
            if v.draft_m <= 0:
                continue

            for bc, b in self.berths.items():
                # Find tide windows where depth + tide >= vessel draft + UKC
                safe_windows = []
                for tw in tides:
                    effective_depth = b.depth_m + (tw.height_m if tw.is_high_tide else 0)
                    if effective_depth >= (v.draft_m + ukc):
                        safe_windows.append(tw)

                if not safe_windows and v.draft_m + ukc > b.depth_m:
                    # No safe tide window for this vessel at this berth
                    self.model.Add(self._x[vid, bc] == 0)
                elif safe_windows:
                    # Start must fall within at least one safe tide window
                    in_window_bools = []
                    for i, tw in enumerate(safe_windows):
                        bv = self.model.NewBoolVar(f"tide_{vid}_{bc}_{i}")
                        self.model.Add(
                            self._start[vid] >= tw.start_min
                        ).OnlyEnforceIf(bv)
                        self.model.Add(
                            self._start[vid] <= tw.end_min
                        ).OnlyEnforceIf(bv)
                        in_window_bools.append(bv)

                    # If assigned to this berth, must be in at least one window
                    if in_window_bools:
                        self.model.Add(
                            sum(in_window_bools) >= 1
                        ).OnlyEnforceIf(self._x[vid, bc])

    # ── Resource Constraints (C8–C10) ──────────────────────────────────

    def add_resource_constraints(self, resources: List[ResourceInput]):
        """
        C8:  Tug availability — cumulative constraint
        C9:  Pilot availability — cumulative constraint
        C10: Channel constraint — max simultaneous movements
        """
        self.resources = resources
        movement_dur = self.config.movement_duration_minutes

        for res in resources:
            # Vessels that need this resource
            if res.resource_type == "tug":
                relevant = [(vid, v) for vid, v in self.vessels.items() if v.needs_tug]
            elif res.resource_type == "pilot":
                relevant = [(vid, v) for vid, v in self.vessels.items() if v.needs_pilot]
            else:
                relevant = list(self.vessels.items())

            if not relevant:
                continue

            # Create movement interval vars (resource used only during movement)
            movement_intervals = []
            demands = []
            for vid, v in relevant:
                mv_end = self.model.NewIntVar(
                    v.eta_minutes + movement_dur,
                    self.config.horizon_minutes + movement_dur,
                    f"mv_end_{res.resource_type}_{vid}",
                )
                self.model.Add(mv_end == self._start[vid] + movement_dur)

                mv_interval = self.model.NewIntervalVar(
                    self._start[vid],
                    movement_dur,
                    mv_end,
                    f"mv_interval_{res.resource_type}_{vid}",
                )
                movement_intervals.append(mv_interval)
                demands.append(1)

            # Cumulative constraint: at most res.capacity concurrent
            if movement_intervals:
                self.model.AddCumulative(
                    movement_intervals, demands, res.capacity
                )

        # C10: Channel constraint (inbound AND outbound movements)
        max_ch = self.config.max_channel_movements
        if max_ch > 0 and self.vessels:
            ch_intervals = []
            ch_demands = []
            for vid, v in self.vessels.items():
                # Inbound movement interval (at start)
                ch_in_end = self.model.NewIntVar(
                    v.eta_minutes + movement_dur,
                    self.config.horizon_minutes + movement_dur,
                    f"ch_in_end_{vid}",
                )
                self.model.Add(ch_in_end == self._start[vid] + movement_dur)

                ch_in_interval = self.model.NewIntervalVar(
                    self._start[vid],
                    movement_dur,
                    ch_in_end,
                    f"ch_in_interval_{vid}",
                )
                ch_intervals.append(ch_in_interval)
                ch_demands.append(1)

                # Outbound movement interval (at end / departure)
                ch_out_end = self.model.NewIntVar(
                    v.eta_minutes + v.service_time_minutes + movement_dur,
                    self.config.horizon_minutes + v.service_time_minutes + movement_dur,
                    f"ch_out_end_{vid}",
                )
                self.model.Add(ch_out_end == self._end[vid] + movement_dur)

                ch_out_interval = self.model.NewIntervalVar(
                    self._end[vid],
                    movement_dur,
                    ch_out_end,
                    f"ch_out_interval_{vid}",
                )
                ch_intervals.append(ch_out_interval)
                ch_demands.append(1)

            self.model.AddCumulative(ch_intervals, ch_demands, max_ch)

    # ── Policy Constraints (C11–C15) ───────────────────────────────────

    def add_policy_constraints(self):
        """
        C11: Customs clearance — vessel must be cleared.
        C12: FCFS ordering — if enabled (globally or per-berth), ETA order respected.
        C13: GoI override — government vessels scheduled first.
        C14: Contract preference — soft bonus for preferred berths.
        C15: SLA commitment — soft penalty for exceeding wait limit.
        """
        # C11: Customs clearance
        for vid, v in self.vessels.items():
            if not v.customs_cleared:
                # Prevent assignment entirely (until cleared)
                for bc in self.berths:
                    self.model.Add(self._x[vid, bc] == 0)

        # C12: FCFS ordering
        if self.config.fcfs_enabled:
            vessel_list = sorted(self.vessels.values(), key=lambda v: v.eta_minutes)
            for i in range(len(vessel_list) - 1):
                v1 = vessel_list[i]
                v2 = vessel_list[i + 1]
                if v1.eta_minutes < v2.eta_minutes:
                    # v1 must start before v2
                    self.model.Add(
                        self._start[v1.vessel_id] <= self._start[v2.vessel_id]
                    )

        # C13: GoI override — government priority vessels start earliest
        if self.config.goi_override_enabled:
            gov_vessels = [v for v in self.vessels.values() if v.government_priority]
            non_gov = [v for v in self.vessels.values() if not v.government_priority]
            for gv in gov_vessels:
                for nv in non_gov:
                    # Government vessel must start before or at same time
                    self.model.Add(
                        self._start[gv.vessel_id] <= self._start[nv.vessel_id]
                    )

    # ── Objective Function ─────────────────────────────────────────────

    def _build_objective(self):
        """
        Multi-objective with BERTH + SHIP-TYPE SPECIFIC weights:
        Minimize: total waiting + SLA penalties + deviation penalty + demurrage
        Maximize: contract preference satisfaction

        When BerthSchedulerConfig has per-berth or per-ship-type configs,
        each (vessel, berth) pair uses for_berth_and_type() to get weights
        specific to that combination. Otherwise, falls back to global config.
        """
        H = self.config.horizon_minutes
        objective_terms = []

        if not self.berth_config.is_per_berth and not self.berth_config.has_ship_type_configs:
            # ── FAST PATH: global weights (no per-berth overhead) ──────
            cfg = self.config

            for vid in self.vessels:
                objective_terms.append(
                    int(cfg.w_waiting * 100) * self._waiting[vid]
                )

            for vid, v in self.vessels.items():
                sla_excess = self.model.NewIntVar(
                    0, H, f"sla_excess_{vid}"
                )
                self.model.AddMaxEquality(sla_excess, [
                    self._waiting[vid] - v.sla_max_wait_minutes,
                    self.model.NewConstant(0),
                ])
                objective_terms.append(
                    int(cfg.w_sla_penalty * 100) * sla_excess
                )

            for vid, v in self.vessels.items():
                if v.preferred_berths:
                    for bc in v.preferred_berths:
                        if bc in self.berths:
                            objective_terms.append(
                                -int(cfg.w_contract_bonus * 100) * self._x[vid, bc]
                            )

            if cfg.w_demurrage > 0:
                for vid, v in self.vessels.items():
                    if v.demurrage_cost_per_hr > 0:
                        cost_factor = int(cfg.w_demurrage * v.demurrage_cost_per_hr / 60 * 100)
                        if cost_factor > 0:
                            objective_terms.append(
                                cost_factor * self._waiting[vid]
                            )

            if cfg.w_deviation > 0 and self.previous_assignments:
                prev_map = {a.vessel_id: a.berth_code for a in self.previous_assignments}
                for vid, prev_bc in prev_map.items():
                    if vid in self.vessels and prev_bc in self.berths:
                        objective_terms.append(
                            int(cfg.w_deviation * 100) * (1 - self._x[vid, prev_bc])
                        )

            # ── Commercial Intelligence terms (NEW) ────────────────────
            self._add_commercial_objective_terms(objective_terms, cfg)

        else:
            # ── PER-BERTH WEIGHTS: each (vessel, berth) pair uses ──────
            # ── that berth's config for objective weighting.       ──────

            for vid, v in self.vessels.items():
                for bc in self.berths:
                    bcfg = self.berth_config.for_berth_and_type(bc, v.vessel_type)
                    w_wait_int = int(bcfg.w_waiting * 100)

                    if w_wait_int > 0:
                        # berth-weighted waiting: bw = waiting[v] if x[v,b]=1 else 0
                        bw = self.model.NewIntVar(0, H, f"bw_{vid}_{bc}")
                        self.model.Add(
                            bw == self._waiting[vid]
                        ).OnlyEnforceIf(self._x[vid, bc])
                        self.model.Add(
                            bw == 0
                        ).OnlyEnforceIf(self._x[vid, bc].Not())
                        objective_terms.append(w_wait_int * bw)

            # SLA penalty — per-berth SLA weight
            for vid, v in self.vessels.items():
                sla_excess = self.model.NewIntVar(
                    0, H, f"sla_excess_{vid}"
                )
                self.model.AddMaxEquality(sla_excess, [
                    self._waiting[vid] - v.sla_max_wait_minutes,
                    self.model.NewConstant(0),
                ])
                for bc in self.berths:
                    bcfg = self.berth_config.for_berth_and_type(bc, v.vessel_type)
                    w_sla_int = int(bcfg.w_sla_penalty * 100)
                    if w_sla_int > 0:
                        bs = self.model.NewIntVar(0, H, f"bsla_{vid}_{bc}")
                        self.model.Add(
                            bs == sla_excess
                        ).OnlyEnforceIf(self._x[vid, bc])
                        self.model.Add(
                            bs == 0
                        ).OnlyEnforceIf(self._x[vid, bc].Not())
                        objective_terms.append(w_sla_int * bs)

            # Contract preference bonus — per-berth weight
            for vid, v in self.vessels.items():
                if v.preferred_berths:
                    for bc in v.preferred_berths:
                        if bc in self.berths:
                            bcfg = self.berth_config.for_berth_and_type(bc, v.vessel_type)
                            objective_terms.append(
                                -int(bcfg.w_contract_bonus * 100) * self._x[vid, bc]
                            )

            # Demurrage — per-berth weight
            for vid, v in self.vessels.items():
                if v.demurrage_cost_per_hr > 0:
                    for bc in self.berths:
                        bcfg = self.berth_config.for_berth_and_type(bc, v.vessel_type)
                        if bcfg.w_demurrage > 0:
                            cost_factor = int(bcfg.w_demurrage * v.demurrage_cost_per_hr / 60 * 100)
                            if cost_factor > 0:
                                bd = self.model.NewIntVar(0, H, f"bdem_{vid}_{bc}")
                                self.model.Add(
                                    bd == self._waiting[vid]
                                ).OnlyEnforceIf(self._x[vid, bc])
                                self.model.Add(
                                    bd == 0
                                ).OnlyEnforceIf(self._x[vid, bc].Not())
                                objective_terms.append(cost_factor * bd)

            # Deviation — use average deviation weight across berths
            avg_dev = sum(
                self.berth_config.for_berth(bc).w_deviation
                for bc in self.berths
            ) / max(len(self.berths), 1)
            if avg_dev > 0 and self.previous_assignments:
                prev_map = {a.vessel_id: a.berth_code for a in self.previous_assignments}
                for vid, prev_bc in prev_map.items():
                    if vid in self.vessels and prev_bc in self.berths:
                        objective_terms.append(
                            int(avg_dev * 100) * (1 - self._x[vid, prev_bc])
                        )

            # ── Commercial Intelligence terms (per-berth path) ─────────
            self._add_commercial_objective_terms(objective_terms, self.config)

        self.model.Minimize(sum(objective_terms))

    def _add_commercial_objective_terms(self, objective_terms: list, cfg: "SchedulerConfig"):
        """
        Add commercial intelligence terms to the CP-SAT objective.

        Terms:
          - Revenue loss: Penalize assigning vessels to berths with lower
            revenue potential (using pattern-based compatibility as proxy)
          - Partnership satisfaction: Bonus for VIP/Premium vessels getting
            preferred berths, penalty for SLA violations
        """
        H = cfg.horizon_minutes

        # ── Revenue loss / commercial term ──
        if cfg.w_commercial > 0:
            w_comm_int = int(cfg.w_commercial * 100)
            for vid, v in self.vessels.items():
                for bc, b in self.berths.items():
                    # Use compatibility score as a proxy for revenue potential.
                    # Lower compatibility → higher penalty (misallocated revenue).
                    if v.vessel_type:
                        compat_score, _, _ = compute_compatibility_score(
                            v.vessel_type, v.cargo_type,
                            b.equipment_types, b.allowed_vessel_types,
                        )
                        # Penalty = (100 - compat) scaled to minutes
                        # Compat 100 → no penalty; compat 30 → penalty 70.
                        penalty = max(0, 100 - compat_score)
                        if penalty > 0:
                            # Apply penalty only when assigned to this berth
                            bp = self.model.NewIntVar(0, 100, f"bcomm_{vid}_{bc}")
                            self.model.Add(
                                bp == penalty
                            ).OnlyEnforceIf(self._x[vid, bc])
                            self.model.Add(
                                bp == 0
                            ).OnlyEnforceIf(self._x[vid, bc].Not())
                            objective_terms.append(w_comm_int * bp)

        # ── Partnership satisfaction term ──
        if cfg.w_partnership > 0:
            w_part_int = int(cfg.w_partnership * 100)
            for vid, v in self.vessels.items():
                # Higher-priority vessels (lower priority number) get bonus
                # for being scheduled early → reduced wait.
                # VIP: priority ~10, Premium: ~50, Standard: ~100
                if v.priority < 100:  # Non-standard priority → partnership vessel
                    priority_bonus = max(0, 100 - v.priority)
                    # Bonus for REDUCED waiting (negative = minimize = good)
                    bp_wait = self.model.NewIntVar(0, H, f"bpart_{vid}")
                    self.model.Add(bp_wait == self._waiting[vid])
                    # Higher priority bonus * actual wait = big penalty for VIP wait
                    objective_terms.append(
                        int(w_part_int * priority_bonus / 100) * bp_wait
                    )

    # ── Solver ─────────────────────────────────────────────────────────

    def add_downtime_constraints(self, downtimes: List[DowntimeWindowInput]):
        """
        C16: No vessel assigned to a berth during its downtime window.
        Prevents start[v] from falling in [dt.start, dt.end - service_time]
        and prevents the vessel interval from overlapping the downtime.
        """
        for dt in downtimes:
            if dt.berth_code not in self.berths:
                continue

            for vid, v in self.vessels.items():
                # If assigned to this berth, vessel interval must not
                # overlap the downtime window.
                # Overlap = NOT (end[v] <= dt.start_min  OR  start[v] >= dt.end_min)
                # So we require: end <= dt.start  OR  start >= dt.end
                before = self.model.NewBoolVar(f"before_dt_{vid}_{dt.berth_code}_{dt.start_min}")
                after = self.model.NewBoolVar(f"after_dt_{vid}_{dt.berth_code}_{dt.start_min}")

                self.model.Add(
                    self._end[vid] <= dt.start_min
                ).OnlyEnforceIf(before)
                self.model.Add(
                    self._start[vid] >= dt.end_min
                ).OnlyEnforceIf(after)

                # If assigned, at least one must be true (before OR after)
                self.model.AddBoolOr([before, after]).OnlyEnforceIf(
                    self._x[vid, dt.berth_code]
                )

    def add_weather_constraints(self, weather_windows: List[WeatherWindowInput]):
        """
        C17: During adverse weather, no vessel can start berthing at ANY berth.
        Treats weather as a global downtime across all berths.
        """
        for ww in weather_windows:
            downtimes = [
                DowntimeWindowInput(
                    berth_code=bc,
                    start_min=ww.start_min,
                    end_min=ww.end_min,
                    reason=ww.reason,
                )
                for bc in self.berths
            ]
            self.add_downtime_constraints(downtimes)

    def add_manual_overrides(self, overrides: List[Tuple[str, str]]):
        """
        Lock vessel→berth assignments for user overrides.

        Args:
            overrides: List of (vessel_id, berth_code) pairs to lock.
                       For each pair, x[v, b] = 1 is enforced.
        """
        for vid, bc in overrides:
            if vid in self.vessels and bc in self.berths:
                key = (vid, bc)
                if key in self._x:
                    self.model.Add(self._x[vid, bc] == 1)

    def build(self):
        """Add all constraints and build objective. Call before solve()."""
        self.add_physical_constraints()
        self.add_temporal_constraints()
        self.add_policy_constraints()
        # NOTE: objective is built last so that deviation/demurrage terms
        # can reference all constraint state.
        self._build_objective()
        return self

    def solve(self, log_search: bool = False) -> SolverResult:
        """Solve the model and return structured results."""
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.berth_config.max_solve_seconds_effective
        if log_search:
            solver.parameters.log_search_progress = True

        status = solver.Solve(self.model)
        status_name = solver.StatusName(status)

        result = SolverResult(
            status=status,
            status_name=status_name,
            solve_time_sec=round(solver.WallTime(), 3),
        )

        if status in (OPTIMAL, FEASIBLE):
            result.objective_value = solver.ObjectiveValue()
            result.assignments = self._extract_assignments(solver)
            result.kpis = self._compute_kpis(result.assignments)
        else:
            # All vessels unassigned
            result.unassigned_vessels = list(self.vessels.keys())

        return result

    def _extract_assignments(self, solver) -> List[AssignmentResult]:
        """Extract vessel→berth assignments from solver solution."""
        assignments = []
        assigned_ids = set()

        for vid, v in self.vessels.items():
            for bc, b in self.berths.items():
                if solver.Value(self._x[vid, bc]) == 1:
                    start_min = solver.Value(self._start[vid])
                    end_min = solver.Value(self._end[vid])
                    wait_min = solver.Value(self._waiting[vid])

                    sla_exceeded = wait_min > v.sla_max_wait_minutes
                    sla_excess = max(0, wait_min - v.sla_max_wait_minutes)

                    assignments.append(AssignmentResult(
                        vessel_id=vid,
                        vessel_name=v.name,
                        berth_code=bc,
                        berth_name=b.berth_name,
                        start_minutes=start_min,
                        end_minutes=end_min,
                        waiting_minutes=wait_min,
                        service_minutes=v.service_time_minutes,
                        sla_exceeded=sla_exceeded,
                        sla_excess_minutes=sla_excess,
                        is_preferred_berth=bc in v.preferred_berths,
                    ))
                    assigned_ids.add(vid)
                    break

        return sorted(assignments, key=lambda a: a.start_minutes)

    def _compute_kpis(self, assignments: List[AssignmentResult]) -> Dict[str, float]:
        """Compute schedule-level KPIs from assignments."""
        if not assignments:
            return {}

        total_wait = sum(a.waiting_minutes for a in assignments)
        avg_wait = total_wait / len(assignments)
        max_wait = max(a.waiting_minutes for a in assignments)
        sla_violations = sum(1 for a in assignments if a.sla_exceeded)

        # Berth utilization
        berth_busy = {}
        for a in assignments:
            berth_busy.setdefault(a.berth_code, 0)
            berth_busy[a.berth_code] += a.service_minutes

        total_berth_capacity = len(self.berths) * self.config.horizon_minutes
        total_busy = sum(berth_busy.values())
        utilization = (total_busy / total_berth_capacity * 100) if total_berth_capacity > 0 else 0

        return {
            "total_vessels": len(assignments),
            "total_waiting_minutes": total_wait,
            "avg_waiting_minutes": round(avg_wait, 1),
            "max_waiting_minutes": max_wait,
            "avg_waiting_hours": round(avg_wait / 60, 2),
            "max_waiting_hours": round(max_wait / 60, 2),
            "sla_violations": sla_violations,
            "sla_compliance_pct": round(
                (1 - sla_violations / len(assignments)) * 100, 1
            ) if assignments else 100.0,
            "berth_utilization_pct": round(utilization, 1),
            "vessels_at_preferred_berth": sum(
                1 for a in assignments if a.is_preferred_berth
            ),
        }


# ── Convenience builder ────────────────────────────────────────────────────

def build_and_solve(
    vessels: List[VesselInput],
    berths: List[BerthInput],
    config,  # SchedulerConfig or BerthSchedulerConfig
    tides: Optional[List[TideWindowInput]] = None,
    resources: Optional[List[ResourceInput]] = None,
    downtimes: Optional[List[DowntimeWindowInput]] = None,
    weather: Optional[List[WeatherWindowInput]] = None,
    previous_assignments: Optional[List[AssignmentResult]] = None,
    manual_overrides: Optional[List[Tuple[str, str]]] = None,
    log_search: bool = False,
) -> SolverResult:
    """
    One-shot build + solve convenience function.

    Example:
        vessels = [VesselInput("V1", loa_m=200, draft_m=10, eta_minutes=0, service_time_minutes=720)]
        berths  = [BerthInput("B1", max_loa_m=250, depth_m=14)]
        result  = build_and_solve(vessels, berths, SchedulerConfig())
    """
    model = BerthConstraintModel(vessels, berths, config, previous_assignments)

    # Add optional constraints BEFORE build() so objective sees full state
    if tides:
        model.add_tide_constraints(tides)
    if resources:
        model.add_resource_constraints(resources)
    if downtimes:
        model.add_downtime_constraints(downtimes)
    if weather:
        model.add_weather_constraints(weather)

    # Apply manual overrides (lock vessel→berth assignments)
    if manual_overrides:
        model.add_manual_overrides(manual_overrides)

    model.build()

    return model.solve(log_search=log_search)
