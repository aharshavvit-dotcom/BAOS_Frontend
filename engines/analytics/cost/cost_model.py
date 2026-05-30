"""
Cost Engine — Demurrage, Revenue, and SLA Cost Modeling.

Computes detailed cost breakdowns for berth assignments:
  - Waiting cost (demurrage per hour)
  - Fuel burn while waiting at anchorage
  - Equipment rental during service
  - SLA penalty for exceeding contractual wait limits
  - Revenue per cargo ton handled
  - Net cost/benefit per assignment

Cost rates are loaded from ports/<port>/cost_config.json when available.
Hardcoded defaults remain as fallbacks but are flagged as ASSUMPTION quality.
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger(__name__)

# ── Cost Parameters ────────────────────────────────────────────────────────

@dataclass
class CostConfig:
    """Port-level cost parameters — loaded from config file or defaults."""
    default_demurrage_per_hr: float = 500.0      # USD/hr
    default_fuel_burn_per_hr: float = 150.0       # USD/hr at anchorage
    default_crane_rate_per_hr: float = 200.0      # USD/hr
    sla_penalty_per_hr: float = 1000.0            # USD/hr over SLA
    government_compliance_penalty: float = 5000.0  # flat USD
    revenue_per_ton: float = 2.5                   # USD/ton cargo
    idle_berth_cost_per_hr: float = 100.0          # USD/hr berth sitting idle
    equipment_switch_cost: float = 500.0           # USD per switch
    source: str = "hardcoded_default"              # Where rates came from

    @classmethod
    def from_json(cls, path: str | Path) -> "CostConfig":
        """Load cost configuration from a JSON file."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Cost config not found at {path} — using hardcoded defaults (ASSUMPTION quality)")
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            default_demurrage_per_hr=data.get("demurrage_per_hour_usd", {}).get("value", 500.0),
            default_fuel_burn_per_hr=data.get("fuel_burn_per_hour_usd", {}).get("value", 150.0),
            default_crane_rate_per_hr=data.get("crane_rate_per_hour_usd", {}).get("value", 200.0),
            sla_penalty_per_hr=data.get("sla_penalty_per_hour_usd", {}).get("value", 1000.0),
            government_compliance_penalty=data.get("government_compliance_penalty_usd", {}).get("value", 5000.0),
            revenue_per_ton=data.get("revenue_per_ton_usd", {}).get("value", 2.5),
            idle_berth_cost_per_hr=data.get("idle_berth_cost_per_hour_usd", {}).get("value", 100.0),
            equipment_switch_cost=data.get("equipment_switch_cost_usd", {}).get("value", 500.0),
            source=str(path),
        )

    @classmethod
    def for_port(cls, port_name: str) -> "CostConfig":
        """Load cost config for a specific port."""
        port_dir = _ROOT / "ports" / port_name.lower().replace(" ", "_")
        config_path = port_dir / "cost_config.json"
        if config_path.exists():
            logger.info(f"Loading cost config from {config_path}")
            return cls.from_json(config_path)
        logger.warning(f"No cost_config.json for port '{port_name}' — using defaults")
        return cls()


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for one vessel assignment."""
    vessel_id: str
    vessel_name: str = ""
    berth_code: str = ""
    # Cost components
    waiting_cost: float = 0.0         # demurrage × wait hours
    fuel_burn_cost: float = 0.0       # fuel rate × wait hours
    equipment_rental: float = 0.0     # crane rate × service hours
    sla_penalty: float = 0.0          # penalty if wait > SLA limit
    compliance_penalty: float = 0.0   # government compliance
    # Revenue
    revenue: float = 0.0              # cargo_tons × rate
    # Totals
    total_cost: float = 0.0
    net_cost: float = 0.0             # total_cost - revenue
    cost_per_ton: float = 0.0         # net_cost / cargo_tons

    def to_dict(self) -> dict:
        return {
            "vessel_id": self.vessel_id,
            "vessel_name": self.vessel_name,
            "berth_code": self.berth_code,
            "waiting_cost": round(self.waiting_cost, 2),
            "fuel_burn_cost": round(self.fuel_burn_cost, 2),
            "equipment_rental": round(self.equipment_rental, 2),
            "sla_penalty": round(self.sla_penalty, 2),
            "compliance_penalty": round(self.compliance_penalty, 2),
            "revenue": round(self.revenue, 2),
            "total_cost": round(self.total_cost, 2),
            "net_cost": round(self.net_cost, 2),
            "cost_per_ton": round(self.cost_per_ton, 2),
        }


@dataclass
class ScheduleCostSummary:
    """Aggregate costs for the full schedule."""
    total_waiting_cost: float = 0.0
    total_fuel_cost: float = 0.0
    total_equipment_cost: float = 0.0
    total_sla_penalties: float = 0.0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    net_cost: float = 0.0
    idle_berth_cost: float = 0.0
    breakdowns: List[CostBreakdown] = field(default_factory=list)


# ── Cost Engine ────────────────────────────────────────────────────────────

class CostEngine:
    """
    Compute costs and revenue for berth assignments.

    Usage:
        engine = CostEngine(CostConfig())
        breakdown = engine.compute_vessel_cost(assignment, vessel_info)
        summary = engine.compute_schedule_cost(assignments, vessels_info, berths, horizon_hours)
    """

    def __init__(self, config: Optional[CostConfig] = None):
        self.config = config or CostConfig()

    def compute_vessel_cost(
        self,
        wait_hours: float,
        service_hours: float,
        cargo_tons: float = 0.0,
        demurrage_rate: float = 0.0,
        sla_max_wait_hours: float = 24.0,
        vessel_id: str = "",
        vessel_name: str = "",
        berth_code: str = "",
    ) -> CostBreakdown:
        """Compute cost breakdown for a single vessel assignment."""
        cfg = self.config
        demurrage = demurrage_rate if demurrage_rate > 0 else cfg.default_demurrage_per_hr

        waiting_cost = demurrage * wait_hours
        fuel_cost = cfg.default_fuel_burn_per_hr * wait_hours
        equipment = cfg.default_crane_rate_per_hr * service_hours

        sla_excess = max(0, wait_hours - sla_max_wait_hours)
        sla_penalty = cfg.sla_penalty_per_hr * sla_excess

        revenue = cargo_tons * cfg.revenue_per_ton
        total_cost = waiting_cost + fuel_cost + equipment + sla_penalty
        net = total_cost - revenue

        return CostBreakdown(
            vessel_id=vessel_id,
            vessel_name=vessel_name,
            berth_code=berth_code,
            waiting_cost=waiting_cost,
            fuel_burn_cost=fuel_cost,
            equipment_rental=equipment,
            sla_penalty=sla_penalty,
            revenue=revenue,
            total_cost=total_cost,
            net_cost=net,
            cost_per_ton=net / cargo_tons if cargo_tons > 0 else 0.0,
        )

    def compute_schedule_cost(
        self,
        assignments: list,
        vessels: dict,
        berths: dict,
        horizon_hours: float = 168.0,
    ) -> ScheduleCostSummary:
        """
        Compute aggregate costs for the full schedule.

        Args:
            assignments: List of AssignmentResult
            vessels: {vessel_id: VesselInput} mapping
            berths: {berth_code: BerthInput} mapping
            horizon_hours: Planning horizon in hours
        """
        summary = ScheduleCostSummary()

        for a in assignments:
            v = vessels.get(a.vessel_id)
            if not v:
                continue

            bd = self.compute_vessel_cost(
                wait_hours=a.waiting_minutes / 60,
                service_hours=a.service_minutes / 60,
                cargo_tons=v.cargo_tons,
                demurrage_rate=v.demurrage_cost_per_hr,
                sla_max_wait_hours=v.sla_max_wait_minutes / 60,
                vessel_id=a.vessel_id,
                vessel_name=a.vessel_name,
                berth_code=a.berth_code,
            )

            summary.breakdowns.append(bd)
            summary.total_waiting_cost += bd.waiting_cost
            summary.total_fuel_cost += bd.fuel_burn_cost
            summary.total_equipment_cost += bd.equipment_rental
            summary.total_sla_penalties += bd.sla_penalty
            summary.total_revenue += bd.revenue

        summary.total_cost = (
            summary.total_waiting_cost + summary.total_fuel_cost +
            summary.total_equipment_cost + summary.total_sla_penalties
        )
        summary.net_cost = summary.total_cost - summary.total_revenue

        # Idle berth cost
        berth_busy_hours = {}
        for a in assignments:
            berth_busy_hours.setdefault(a.berth_code, 0)
            berth_busy_hours[a.berth_code] += a.service_minutes / 60

        total_idle = 0
        for bc in berths:
            busy = berth_busy_hours.get(bc, 0)
            idle = max(0, horizon_hours - busy)
            total_idle += idle

        summary.idle_berth_cost = total_idle * self.config.idle_berth_cost_per_hr

        return summary
