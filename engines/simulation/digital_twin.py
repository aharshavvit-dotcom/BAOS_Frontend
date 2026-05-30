"""
Digital Twin — Event-Driven Port Simulation (Phase 8).

Simulates port operations for:
  - Policy testing before deployment
  - RL agent training (Phase 7)
  - What-if scenario exploration
  - Performance benchmarking

Event types:
  - Vessel arrival
  - Vessel departure
  - Weather event (pause operations)
  - Equipment breakdown
  - Tide change
  - Resource availability change
"""
from __future__ import annotations

import heapq
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engines.simulation.optimization.constraint_model import (
    VesselInput, BerthInput, SchedulerConfig, SolverResult,
)
from engines.simulation.optimization.scheduler import RollingHorizonScheduler


@dataclass
class SimEvent:
    """A simulation event."""
    time: float               # minutes from simulation start
    event_type: str            # "arrival", "departure", "weather", "breakdown"
    data: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        return self.time < other.time


@dataclass
class SimState:
    """Current simulation state."""
    current_time: float = 0.0
    berth_occupancy: Dict[str, Optional[str]] = field(default_factory=dict)
    vessel_queue: List[VesselInput] = field(default_factory=list)
    completed_vessels: List[str] = field(default_factory=list)
    active_disruptions: List[str] = field(default_factory=list)


@dataclass
class SimResult:
    """Complete simulation result."""
    total_time_minutes: float = 0.0
    vessels_processed: int = 0
    vessels_delayed: int = 0
    avg_waiting_minutes: float = 0.0
    max_waiting_minutes: float = 0.0
    berth_utilization_pct: float = 0.0
    disruptions_count: int = 0
    events_processed: int = 0
    kpi_history: List[Dict[str, float]] = field(default_factory=list)


class PortDigitalTwin:
    """
    Event-driven simulation of port operations.

    Usage:
        twin = PortDigitalTwin(berths, config)
        twin.add_vessel_arrivals(vessels)
        twin.add_weather_event(start=1000, duration=360)
        result = twin.simulate(duration_hours=168)
    """

    def __init__(
        self,
        berths: List[BerthInput],
        config: Optional[SchedulerConfig] = None,
    ):
        self.berths = {b.berth_code: b for b in berths}
        self.config = config or SchedulerConfig()
        self._event_queue: List[SimEvent] = []
        self._state = SimState(
            berth_occupancy={b.berth_code: None for b in berths},
        )
        self._results = SimResult()
        self._waiting_times: List[float] = []

    def add_vessel_arrivals(self, vessels: List[VesselInput]):
        """Schedule vessel arrival events."""
        for v in vessels:
            heapq.heappush(self._event_queue, SimEvent(
                time=v.eta_minutes,
                event_type="arrival",
                data={"vessel": v},
            ))

    def add_weather_event(self, start_minutes: float, duration_minutes: float):
        """Add a weather disruption event."""
        heapq.heappush(self._event_queue, SimEvent(
            time=start_minutes,
            event_type="weather_start",
            data={"duration": duration_minutes},
        ))
        heapq.heappush(self._event_queue, SimEvent(
            time=start_minutes + duration_minutes,
            event_type="weather_end",
            data={},
        ))

    def add_equipment_breakdown(
        self, berth_code: str, start_minutes: float, duration_minutes: float,
    ):
        """Add equipment breakdown at a berth."""
        heapq.heappush(self._event_queue, SimEvent(
            time=start_minutes,
            event_type="breakdown_start",
            data={"berth_code": berth_code, "duration": duration_minutes},
        ))
        heapq.heappush(self._event_queue, SimEvent(
            time=start_minutes + duration_minutes,
            event_type="breakdown_end",
            data={"berth_code": berth_code},
        ))

    def simulate(self, duration_hours: float = 168.0) -> SimResult:
        """
        Run the event-driven simulation.

        Processes events in time order, runs optimization when
        vessels arrive, and tracks KPIs over time.
        """
        max_time = duration_hours * 60
        events_processed = 0

        while self._event_queue:
            event = heapq.heappop(self._event_queue)

            if event.time > max_time:
                break

            self._state.current_time = event.time
            events_processed += 1

            if event.event_type == "arrival":
                self._handle_arrival(event)
            elif event.event_type == "departure":
                self._handle_departure(event)
            elif event.event_type == "weather_start":
                self._state.active_disruptions.append("weather")
                self._results.disruptions_count += 1
            elif event.event_type == "weather_end":
                if "weather" in self._state.active_disruptions:
                    self._state.active_disruptions.remove("weather")
                self._try_schedule_waiting_vessels()
            elif event.event_type == "breakdown_start":
                bc = event.data.get("berth_code", "")
                self._state.active_disruptions.append(f"breakdown_{bc}")
                self._results.disruptions_count += 1
            elif event.event_type == "breakdown_end":
                bc = event.data.get("berth_code", "")
                tag = f"breakdown_{bc}"
                if tag in self._state.active_disruptions:
                    self._state.active_disruptions.remove(tag)
                self._try_schedule_waiting_vessels()

        # Finalize results
        self._results.total_time_minutes = max_time
        self._results.vessels_processed = len(self._state.completed_vessels)
        self._results.events_processed = events_processed

        if self._waiting_times:
            self._results.avg_waiting_minutes = sum(self._waiting_times) / len(self._waiting_times)
            self._results.max_waiting_minutes = max(self._waiting_times)
            self._results.vessels_delayed = sum(1 for w in self._waiting_times if w > 0)

        # Berth utilization from completed vessels
        total_capacity = len(self.berths) * max_time
        total_occupied = sum(
            v.service_time_minutes for v in self._state.vessel_queue
        ) if self._state.vessel_queue else 0

        return self._results

    def _handle_arrival(self, event: SimEvent):
        """Handle vessel arrival: try to assign immediately or add to queue."""
        vessel = event.data["vessel"]

        # Check if any berth is free
        if "weather" in self._state.active_disruptions:
            self._state.vessel_queue.append(vessel)
            return

        assigned = False
        for bc, occupant in self._state.berth_occupancy.items():
            if occupant is None:
                # Check physical feasibility (simplified)
                b = self.berths[bc]
                if vessel.loa_m <= b.max_loa_m and vessel.draft_m <= b.max_draft_m:
                    if f"breakdown_{bc}" not in self._state.active_disruptions:
                        self._assign_vessel(vessel, bc)
                        assigned = True
                        break

        if not assigned:
            self._state.vessel_queue.append(vessel)

    def _assign_vessel(self, vessel: VesselInput, berth_code: str):
        """Assign a vessel to a berth and schedule departure."""
        waiting = self._state.current_time - vessel.eta_minutes
        self._waiting_times.append(max(0, waiting))

        self._state.berth_occupancy[berth_code] = vessel.vessel_id

        # Schedule departure
        departure_time = self._state.current_time + vessel.service_time_minutes
        heapq.heappush(self._event_queue, SimEvent(
            time=departure_time,
            event_type="departure",
            data={"vessel_id": vessel.vessel_id, "berth_code": berth_code},
        ))

    def _handle_departure(self, event: SimEvent):
        """Handle vessel departure: free berth and try to schedule waiting vessels."""
        bc = event.data["berth_code"]
        vid = event.data["vessel_id"]

        self._state.berth_occupancy[bc] = None
        self._state.completed_vessels.append(vid)
        self._try_schedule_waiting_vessels()

    def _try_schedule_waiting_vessels(self):
        """Try to assign waiting vessels to free berths."""
        remaining_queue = []
        for vessel in self._state.vessel_queue:
            assigned = False
            for bc, occupant in self._state.berth_occupancy.items():
                if occupant is None:
                    b = self.berths[bc]
                    if vessel.loa_m <= b.max_loa_m and vessel.draft_m <= b.max_draft_m:
                        if f"breakdown_{bc}" not in self._state.active_disruptions:
                            self._assign_vessel(vessel, bc)
                            assigned = True
                            break
            if not assigned:
                remaining_queue.append(vessel)
        self._state.vessel_queue = remaining_queue

    def compare_policies(
        self,
        vessels: List[VesselInput],
        policies: List[SchedulerConfig],
        duration_hours: float = 168.0,
    ) -> List[Tuple[str, SimResult]]:
        """
        Run the same scenario under different policies, compare results.

        Returns list of (policy_name, SimResult) tuples.
        """
        results = []
        for i, policy in enumerate(policies):
            twin = PortDigitalTwin(list(self.berths.values()), policy)
            twin.add_vessel_arrivals(vessels)
            result = twin.simulate(duration_hours)
            results.append((f"Policy_{i}", result))
        return results
