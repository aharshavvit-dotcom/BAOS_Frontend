"""
KPI Calculator — Phase 11: Real-time KPI Computation.

Tracks and computes:
  - Average / max waiting time
  - Berth utilization %
  - Revenue per hour
  - Conflict rate
  - SLA compliance %
  - Risk exposure index
  - Equipment utilization %
  - Throughput (tons/hour)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from optimization_engine.constraint_model import SolverResult, AssignmentResult
from cost_engine.cost_model import CostEngine, CostConfig, ScheduleCostSummary


@dataclass
class KPIDashboard:
    """Full KPI dashboard output."""
    # Operational KPIs
    avg_waiting_hours: float = 0.0
    max_waiting_hours: float = 0.0
    total_vessels: int = 0
    vessels_assigned: int = 0
    vessels_unassigned: int = 0
    # Utilization
    berth_utilization_pct: float = 0.0
    equipment_utilization_pct: float = 0.0
    # Quality
    sla_compliance_pct: float = 100.0
    sla_violations: int = 0
    conflict_rate: float = 0.0
    # Financial
    total_revenue: float = 0.0
    total_cost: float = 0.0
    net_cost: float = 0.0
    revenue_per_hour: float = 0.0
    cost_per_vessel: float = 0.0
    # Throughput
    throughput_tons_per_hour: float = 0.0
    total_cargo_tons: float = 0.0
    # Risk
    risk_exposure_index: float = 0.0
    avg_constraint_margin: float = 0.0
    # Schedule
    preferred_berth_pct: float = 0.0
    solver_status: str = ""
    solve_time_sec: float = 0.0

    def to_dict(self) -> dict:
        return {k: round(v, 2) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


class KPICalculator:
    """
    Compute comprehensive KPIs from optimization results.

    Usage:
        calc = KPICalculator()
        dashboard = calc.compute(solver_result, vessels, berths, cost_summary)
    """

    def __init__(self, cost_config: Optional[CostConfig] = None):
        self.cost_engine = CostEngine(cost_config)

    def compute(
        self,
        result: SolverResult,
        vessels: Dict[str, any],
        berths: Dict[str, any],
        horizon_hours: float = 168.0,
        cost_summary: Optional[ScheduleCostSummary] = None,
    ) -> KPIDashboard:
        """Compute full KPI dashboard from solver result."""
        dash = KPIDashboard()

        assignments = result.assignments
        dash.total_vessels = len(vessels)
        dash.vessels_assigned = len(assignments)
        dash.vessels_unassigned = len(result.unassigned_vessels)
        dash.solver_status = result.status_name
        dash.solve_time_sec = result.solve_time_sec

        if not assignments:
            return dash

        # Waiting times
        wait_hours = [a.waiting_minutes / 60 for a in assignments]
        dash.avg_waiting_hours = sum(wait_hours) / len(wait_hours)
        dash.max_waiting_hours = max(wait_hours)

        # SLA
        sla_viol = sum(1 for a in assignments if a.sla_exceeded)
        dash.sla_violations = sla_viol
        dash.sla_compliance_pct = round(
            (1 - sla_viol / len(assignments)) * 100, 1
        )

        # Berth utilization
        berth_busy = {}
        for a in assignments:
            berth_busy.setdefault(a.berth_code, 0)
            berth_busy[a.berth_code] += a.service_minutes / 60

        total_capacity = len(berths) * horizon_hours
        total_busy = sum(berth_busy.values())
        dash.berth_utilization_pct = round(
            (total_busy / total_capacity * 100) if total_capacity > 0 else 0, 1
        )

        # Preferred berth
        pref = sum(1 for a in assignments if a.is_preferred_berth)
        dash.preferred_berth_pct = round(
            (pref / len(assignments) * 100) if assignments else 0, 1
        )

        # Financial KPIs (from cost summary if provided)
        if cost_summary:
            dash.total_revenue = cost_summary.total_revenue
            dash.total_cost = cost_summary.total_cost
            dash.net_cost = cost_summary.net_cost
            dash.revenue_per_hour = round(
                cost_summary.total_revenue / horizon_hours
                if horizon_hours > 0 else 0, 2
            )
            dash.cost_per_vessel = round(
                cost_summary.total_cost / len(assignments)
                if assignments else 0, 2
            )

        # Throughput
        total_cargo = sum(
            vessels[a.vessel_id].cargo_tons
            for a in assignments
            if a.vessel_id in vessels and hasattr(vessels[a.vessel_id], 'cargo_tons')
        )
        dash.total_cargo_tons = total_cargo
        dash.throughput_tons_per_hour = round(
            total_cargo / horizon_hours if horizon_hours > 0 else 0, 1
        )

        # Risk exposure (from KPIs dict)
        if result.kpis:
            dash.risk_exposure_index = result.kpis.get("risk_score", 0)

        return dash
