"""
Optimizer background tasks — async CP-SAT optimization.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Add project root for engine imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@celery_app.task(
    bind=True,
    name="tasks.optimizer_tasks.run_optimization",
    time_limit=120,
    soft_time_limit=90,
)
def run_optimization(self, port_code: str, vessels: list, config: Dict[str, Any] = None):
    """
    Run CP-SAT multi-vessel optimization in background.
    Returns task_id that frontend can poll for status.
    """
    logger.info(f"Starting optimization for port {port_code} with {len(vessels)} vessels")
    self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Loading port config..."})

    try:
        from backend.db.repositories.port_store import load_port_config, port_exists
        from engines.simulation.optimization.constraint_model import (
            VesselInput, BerthInput, SchedulerConfig, ResourceInput,
            build_and_solve, OPTIMAL, FEASIBLE,
        )
        from engines.simulation.optimization.scheduler import RollingHorizonScheduler

        if not port_exists(port_code):
            return {"status": "error", "message": f"Port '{port_code}' not found"}

        self.update_state(state="PROGRESS", meta={"progress": 30, "message": "Building model..."})

        cfg = load_port_config(port_code)
        berths = []
        for b in cfg.get("berths", []):
            berths.append(BerthInput(
                berth_code=b.get("berth_code", ""),
                berth_name=b.get("berth_name", ""),
                max_loa_m=float(b.get("max_loa_m", 300)),
                max_beam_m=float(b.get("max_beam_m", 50)),
                max_draft_m=float(b.get("max_draft_m", 15)),
                depth_m=float(b.get("depth_m", 15)),
                allowed_vessel_types=b.get("allowed_vessel_types", []),
                allow_24x7=b.get("allow_24x7", True),
            ))

        vessel_inputs = []
        for v in vessels:
            vessel_inputs.append(VesselInput(
                vessel_id=v.get("vessel_id", ""),
                name=v.get("name", ""),
                vessel_type=v.get("vessel_type", ""),
                loa_m=v.get("loa_m", 0),
                beam_m=v.get("beam_m", 0),
                draft_m=v.get("draft_m", 0),
                cargo_type=v.get("cargo_type", ""),
                cargo_tons=v.get("cargo_tons", 0),
                eta_minutes=v.get("eta_minutes", 0),
                service_time_minutes=v.get("service_time_minutes", 720),
                priority=v.get("priority", 100),
            ))

        self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Running solver..."})

        scheduler_config = SchedulerConfig()
        if config:
            for k, v in config.items():
                if hasattr(scheduler_config, k):
                    setattr(scheduler_config, k, v)

        scheduler = RollingHorizonScheduler(scheduler_config)
        resources = [
            ResourceInput("pilot", capacity=2),
            ResourceInput("tug", capacity=3),
        ]
        snapshot = scheduler.optimize(vessel_inputs, berths, resources=resources)
        result = snapshot.solver_result

        self.update_state(state="PROGRESS", meta={"progress": 90, "message": "Generating results..."})

        if result is None:
            return {"status": "error", "message": "Solver returned no result"}

        assignments = []
        for a in result.assignments:
            assignments.append({
                "vessel_id": a.vessel_id,
                "vessel_name": a.vessel_name,
                "berth_code": a.berth_code,
                "berth_name": a.berth_name,
                "start_minutes": a.start_minutes,
                "end_minutes": a.end_minutes,
                "waiting_minutes": a.waiting_minutes,
                "service_minutes": a.service_minutes,
                "sla_exceeded": a.sla_exceeded,
            })

        return {
            "status": result.status_name,
            "solve_time_sec": result.solve_time_sec,
            "objective_value": result.objective_value,
            "assignments": assignments,
            "unassigned_vessels": result.unassigned_vessels,
            "kpis": result.kpis,
        }

    except Exception as exc:
        logger.error(f"Optimization failed: {exc}")
        return {"status": "error", "message": str(exc)}
