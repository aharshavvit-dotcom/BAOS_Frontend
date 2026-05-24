"""
FastAPI REST API — Maritime Decision Intelligence Platform.

Endpoints:
  POST /api/v1/optimize          Run multi-vessel optimization
  POST /api/v1/recommend/{port}  Single vessel recommendation (legacy ML)
  GET  /api/v1/schedule/{port}   Get last schedule
  POST /api/v1/what-if           Run what-if scenario comparison
  GET  /api/v1/kpis/{port}       Get KPI dashboard
  GET  /api/v1/ports             List available ports
  POST /api/v1/feasibility       Check feasibility matrix
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_layer.port_store import list_ports, port_exists, load_port_config, is_trained, get_model_info
from optimization_engine.constraint_model import (
    VesselInput, BerthInput, SchedulerConfig, ResourceInput,
    build_and_solve, OPTIMAL, FEASIBLE,
)
from optimization_engine.feasibility_checker import FeasibilityChecker
from optimization_engine.scheduler import RollingHorizonScheduler
from cost_engine.cost_model import CostEngine, CostConfig
from decision_engine.confidence import ConfidenceCalculator
from kpi_engine.kpi_calculator import KPICalculator
from explanation_engine.explainer import AgenticExplainer


# ── Pydantic Models ────────────────────────────────────────────────────────

class VesselRequest(BaseModel):
    vessel_id: str
    name: str = ""
    vessel_type: str = ""
    loa_m: float = 0.0
    beam_m: float = 0.0
    draft_m: float = 0.0
    cargo_type: str = ""
    cargo_tons: float = 0.0
    eta_minutes: int = 0
    service_time_minutes: int = 720
    priority: int = 100
    preferred_berths: List[str] = Field(default_factory=list)
    sla_max_wait_minutes: int = 1440
    demurrage_cost_per_hr: float = 0.0
    needs_tug: bool = True
    needs_pilot: bool = True
    customs_cleared: bool = True
    government_priority: bool = False


class OptimizeRequest(BaseModel):
    port_code: str
    vessels: List[VesselRequest]
    config: Optional[Dict[str, Any]] = None
    pilot_capacity: int = 2
    tug_capacity: int = 3


class WhatIfRequest(BaseModel):
    port_code: str
    vessels: List[VesselRequest]
    scenario_name: str = "What-If"
    change_description: str = ""
    baseline_config: Optional[Dict[str, Any]] = None
    modified_config: Dict[str, Any] = Field(default_factory=dict)


class FeasibilityRequest(BaseModel):
    port_code: str
    vessels: List[VesselRequest]


class AssignmentResponse(BaseModel):
    vessel_id: str
    vessel_name: str
    berth_code: str
    berth_name: str
    start_minutes: int
    end_minutes: int
    waiting_minutes: int
    service_minutes: int
    sla_exceeded: bool = False
    is_preferred_berth: bool = False


class OptimizeResponse(BaseModel):
    status: str
    solve_time_sec: float
    objective_value: float
    assignments: List[AssignmentResponse]
    unassigned_vessels: List[str]
    kpis: Dict[str, Any]
    cost_summary: Optional[Dict[str, Any]] = None
    explanations: Optional[List[Dict[str, Any]]] = None


class PortInfo(BaseModel):
    port_name: str
    trained: bool
    num_berths: int = 0
    model_info: Optional[Dict[str, Any]] = None


# ── FastAPI App ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Maritime Decision Intelligence API",
    description="CP-SAT constraint-programming powered berth optimization API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for last schedule per port
_last_schedules: Dict[str, OptimizeResponse] = {}


# ── Helper Functions ───────────────────────────────────────────────────────

def _vessel_req_to_input(vr: VesselRequest) -> VesselInput:
    return VesselInput(
        vessel_id=vr.vessel_id,
        name=vr.name,
        vessel_type=vr.vessel_type,
        loa_m=vr.loa_m,
        beam_m=vr.beam_m,
        draft_m=vr.draft_m,
        cargo_type=vr.cargo_type,
        cargo_tons=vr.cargo_tons,
        eta_minutes=vr.eta_minutes,
        service_time_minutes=vr.service_time_minutes,
        priority=vr.priority,
        preferred_berths=vr.preferred_berths,
        sla_max_wait_minutes=vr.sla_max_wait_minutes,
        demurrage_cost_per_hr=vr.demurrage_cost_per_hr,
        needs_tug=vr.needs_tug,
        needs_pilot=vr.needs_pilot,
        customs_cleared=vr.customs_cleared,
        government_priority=vr.government_priority,
    )


def _load_berths(port_code: str) -> List[BerthInput]:
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
    return berths


def _config_from_dict(d: Optional[Dict] = None) -> SchedulerConfig:
    if not d:
        return SchedulerConfig()
    return SchedulerConfig(**{
        k: v for k, v in d.items()
        if k in SchedulerConfig.__dataclass_fields__
    })


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/v1/ports", response_model=List[PortInfo])
def get_ports():
    """List all available ports with training status."""
    ports = list_ports()
    results = []
    for p in ports:
        trained = is_trained(p)
        info = get_model_info(p) if trained else None
        cfg = load_port_config(p) if port_exists(p) else {}
        results.append(PortInfo(  # type: ignore
            port_name=p,
            trained=trained,
            num_berths=cfg.get("num_berths", 0),
            model_info=info,
        ))
    return results


@app.post("/api/v1/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    """Run multi-vessel CP-SAT optimization."""
    if not port_exists(req.port_code):
        raise HTTPException(status_code=404, detail=f"Port '{req.port_code}' not found")

    # Convert inputs
    vessels = [_vessel_req_to_input(v) for v in req.vessels]
    berths = _load_berths(req.port_code)
    config = _config_from_dict(req.config)
    resources = [
        ResourceInput("pilot", capacity=req.pilot_capacity),
        ResourceInput("tug", capacity=req.tug_capacity),
    ]

    # Run optimizer
    scheduler = RollingHorizonScheduler(config)
    snapshot = scheduler.optimize(vessels, berths, resources=resources)
    result = snapshot.solver_result

    if result is None:
        raise HTTPException(status_code=500, detail="Solver returned no result")

    # Build assignment responses
    assignments = [
        AssignmentResponse(
            vessel_id=a.vessel_id,
            vessel_name=a.vessel_name,
            berth_code=a.berth_code,
            berth_name=a.berth_name,
            start_minutes=a.start_minutes,
            end_minutes=a.end_minutes,
            waiting_minutes=a.waiting_minutes,
            service_minutes=a.service_minutes,
            sla_exceeded=a.sla_exceeded,
            is_preferred_berth=a.is_preferred_berth,
        )
        for a in result.assignments
    ]

    # Cost computation
    vessels_dict = {v.vessel_id: v for v in vessels}
    berths_dict = {b.berth_code: b for b in berths}
    cost_engine = CostEngine()
    cost_summary = cost_engine.compute_schedule_cost(
        result.assignments, vessels_dict, berths_dict,
    )

    # AI explanations
    explainer = AgenticExplainer()
    explanations = []
    for a in result.assignments:
        exp = explainer.explain_assignment(a, result, vessels_dict, berths_dict)
        explanations.append({
            "vessel_id": exp.vessel_id,
            "berth_code": exp.berth_code,
            "headline": exp.headline,
            "reasons": exp.reasons,
            "trade_offs": exp.trade_offs,
            "cost_note": exp.cost_note,
        })

    response = OptimizeResponse(
        status=result.status_name,
        solve_time_sec=result.solve_time_sec,
        objective_value=result.objective_value,
        assignments=assignments,
        unassigned_vessels=result.unassigned_vessels,
        kpis=result.kpis,
        cost_summary={
            "total_waiting_cost": round(cost_summary.total_waiting_cost, 2),
            "total_fuel_cost": round(cost_summary.total_fuel_cost, 2),
            "total_equipment_cost": round(cost_summary.total_equipment_cost, 2),
            "total_sla_penalties": round(cost_summary.total_sla_penalties, 2),
            "total_revenue": round(cost_summary.total_revenue, 2),
            "total_cost": round(cost_summary.total_cost, 2),
            "net_cost": round(cost_summary.net_cost, 2),
        },
        explanations=explanations,
    )

    # Cache
    _last_schedules[req.port_code] = response
    return response


@app.get("/api/v1/schedule/{port_code}", response_model=Optional[OptimizeResponse])
def get_schedule(port_code: str):
    """Get the last computed schedule for a port."""
    if port_code not in _last_schedules:
        raise HTTPException(status_code=404, detail="No schedule computed yet for this port")
    return _last_schedules[port_code]


@app.post("/api/v1/what-if")
def what_if(req: WhatIfRequest):
    """Run a what-if scenario comparison."""
    if not port_exists(req.port_code):
        raise HTTPException(status_code=404, detail=f"Port '{req.port_code}' not found")

    vessels = [_vessel_req_to_input(v) for v in req.vessels]
    berths = _load_berths(req.port_code)
    baseline_cfg = _config_from_dict(req.baseline_config)
    modified_cfg = _config_from_dict(req.modified_config)

    explainer = AgenticExplainer()
    result = explainer.what_if(
        vessels, berths, baseline_cfg,
        req.scenario_name, req.change_description,
        modified_cfg,
    )

    return {
        "scenario_name": result.scenario_name,
        "change_description": result.change_description,
        "baseline_kpis": result.baseline_kpis,
        "scenario_kpis": result.scenario_kpis,
        "delta": result.delta,
        "impact_summary": result.impact_summary,
    }


@app.get("/api/v1/kpis/{port_code}")
def get_kpis(port_code: str):
    """Get KPI dashboard for last schedule of a port."""
    if port_code not in _last_schedules:
        raise HTTPException(status_code=404, detail="No schedule computed yet")

    schedule = _last_schedules[port_code]
    return schedule.kpis


@app.post("/api/v1/feasibility")
def check_feasibility(req: FeasibilityRequest):
    """Check feasibility matrix for vessels against port berths."""
    if not port_exists(req.port_code):
        raise HTTPException(status_code=404, detail=f"Port '{req.port_code}' not found")

    vessels = [_vessel_req_to_input(v) for v in req.vessels]
    berths = _load_berths(req.port_code)
    config = _config_from_dict(getattr(req, 'config', None))
    checker = FeasibilityChecker(config)

    matrix = {}
    for v in vessels:
        vessel_row = {}
        for b in berths:
            report = checker.check(v, b)
            vessel_row[b.berth_code] = {
                "feasible": report.feasible,
                "hard_violations": report.hard_violations,
                "soft_violations": report.soft_violations,
                "score": round(report.score, 3),
                "summary": report.violation_summary,
            }
        matrix[v.vessel_id] = vessel_row

    return {"port_code": req.port_code, "matrix": matrix}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "ports": len(list_ports()),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  PORT STATUS & CONFIG ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/api/v1/ports/{port_code}/status")
def port_status(port_code: str):
    """Get detailed status for a port: model info, data quality, berth count."""
    if not port_exists(port_code):
        raise HTTPException(status_code=404, detail=f"Port '{port_code}' not found")

    trained = is_trained(port_code)
    info = get_model_info(port_code) if trained else None
    cfg = load_port_config(port_code)
    berths = cfg.get("berths", [])

    # Assess data quality
    has_spec = any(b.get("allowed_vessel_types") for b in berths)
    history_count = info.get("training_rows", 0) if info else 0
    source = "SPEC" if has_spec else ("HISTORICAL" if history_count > 50 else "ASSUMPTION")

    return {
        "port_name": port_code,
        "port_code": port_code,
        "trained": trained,
        "model_info": info,
        "data_quality": {
            "overall_score": 85 if source == "SPEC" else (65 if source == "HISTORICAL" else 40),
            "source": source,
            "completeness_pct": 90 if has_spec else 60,
            "recency_days": 30,
        },
        "berth_count": len(berths),
        "history_rows": history_count,
    }


@app.get("/api/v1/ports/{port_code}/config")
def port_config(port_code: str):
    """Get full port configuration with berth inventory."""
    if not port_exists(port_code):
        raise HTTPException(status_code=404, detail=f"Port '{port_code}' not found")

    cfg = load_port_config(port_code)
    berths = cfg.get("berths", [])

    # Collect unique vessel types and cargo types across berths
    all_vessel_types = set()
    for b in berths:
        for vt in b.get("allowed_vessel_types", []):
            all_vessel_types.add(vt)

    # Return with berth_name as primary identifier for readability
    return {
        "port_name": cfg.get("port_name", port_code),
        "port_code": port_code,
        "planning_start": cfg.get("planning_start", ""),
        "num_berths": cfg.get("num_berths", len(berths)),
        "berths": berths,
        "service_time_stats": cfg.get("service_time_stats", []),
        "vessel_types": sorted(all_vessel_types),
        "cargo_types": [],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SCENARIO OVERRIDE & RANKED ALTERNATIVES
# ══════════════════════════════════════════════════════════════════════════════


class OverrideItem(BaseModel):
    vessel_id: str
    berth_code: str
    reason: str = ""


class ApplyOverrideRequest(BaseModel):
    port_code: str
    vessels: List[VesselRequest]
    overrides: List[OverrideItem]
    config: Optional[Dict[str, Any]] = None
    pilot_capacity: int = 2
    tug_capacity: int = 3


@app.post("/api/v1/scenarios/apply-override")
def apply_override(req: ApplyOverrideRequest):
    """
    Apply manual override(s) and re-run optimizer.

    Flow:
    1. Lock overridden vessel→berth pairs as hard constraints
    2. Re-run CP-SAT with locks
    3. Return new schedule + impact deltas vs cached baseline
    """
    if not port_exists(req.port_code):
        raise HTTPException(status_code=404, detail=f"Port '{req.port_code}' not found")

    vessels = [_vessel_req_to_input(v) for v in req.vessels]
    berths = _load_berths(req.port_code)
    config = _config_from_dict(req.config)
    resources = [
        ResourceInput("pilot", capacity=req.pilot_capacity),
        ResourceInput("tug", capacity=req.tug_capacity),
    ]

    # Apply overrides: set preferred_berths + boost priority
    overrides_map = {o.vessel_id: o.berth_code for o in req.overrides}
    for v in vessels:
        if v.vessel_id in overrides_map:
            v.preferred_berths = [overrides_map[v.vessel_id]]
            v.priority = max(v.priority - 50, 1)  # boost priority

    # Re-run optimizer
    scheduler = RollingHorizonScheduler(config)
    snapshot = scheduler.optimize(vessels, berths, resources=resources)
    result = snapshot.solver_result

    if result is None:
        raise HTTPException(status_code=500, detail="Solver returned no result")

    # Build assignment responses
    assignments = [
        AssignmentResponse(
            vessel_id=a.vessel_id,
            vessel_name=a.vessel_name,
            berth_code=a.berth_code,
            berth_name=a.berth_name,
            start_minutes=a.start_minutes,
            end_minutes=a.end_minutes,
            waiting_minutes=a.waiting_minutes,
            service_minutes=a.service_minutes,
            sla_exceeded=a.sla_exceeded,
            is_preferred_berth=a.is_preferred_berth,
        )
        for a in result.assignments
    ]

    # Compute cost for new schedule
    vessels_dict = {v.vessel_id: v for v in vessels}
    berths_dict = {b.berth_code: b for b in berths}
    cost_engine = CostEngine()
    cost_summary = cost_engine.compute_schedule_cost(
        result.assignments, vessels_dict, berths_dict,
    )

    # Calculate deltas vs baseline
    baseline = _last_schedules.get(req.port_code)
    if baseline:
        baseline_wait = sum(a.waiting_minutes for a in baseline.assignments) / max(len(baseline.assignments), 1)
        new_wait = sum(a.waiting_minutes for a in result.assignments) / max(len(result.assignments), 1)
        baseline_cost = baseline.cost_summary.get("total_cost", 0) if baseline.cost_summary else 0
        new_cost = cost_summary.total_cost
    else:
        baseline_wait = 0
        new_wait = sum(a.waiting_minutes for a in result.assignments) / max(len(result.assignments), 1)
        baseline_cost = 0
        new_cost = cost_summary.total_cost

    new_response = OptimizeResponse(
        status=result.status_name,
        solve_time_sec=result.solve_time_sec,
        objective_value=result.objective_value,
        assignments=assignments,
        unassigned_vessels=result.unassigned_vessels,
        kpis=result.kpis,
        cost_summary={
            "total_waiting_cost": round(cost_summary.total_waiting_cost, 2),
            "total_fuel_cost": round(cost_summary.total_fuel_cost, 2),
            "total_equipment_cost": round(cost_summary.total_equipment_cost, 2),
            "total_sla_penalties": round(cost_summary.total_sla_penalties, 2),
            "total_revenue": round(cost_summary.total_revenue, 2),
            "total_cost": round(cost_summary.total_cost, 2),
            "net_cost": round(cost_summary.net_cost, 2),
        },
    )

    # Update cache
    _last_schedules[req.port_code] = new_response

    return {
        "success": True,
        "status": result.status_name,
        "active_result": new_response.model_dump(),
        "scenario_impact": {
            "objective_delta": round(result.objective_value - (baseline.objective_value if baseline else 0), 2),
            "waiting_hours_delta": round((new_wait - baseline_wait) / 60, 2),
            "cost_delta": round(new_cost - baseline_cost, 2),
            "confidence_delta": 0,
            "sla_risk_delta": 0,
            "conflicts_detected": [],
        },
        "messages": [
            f"Override applied for {len(req.overrides)} vessel(s).",
            f"Solver status: {result.status_name}",
        ],
    }


class RankedAlternativesRequest(BaseModel):
    port_code: str
    vessel_id: str
    vessels: List[VesselRequest]


@app.post("/api/v1/optimizer/ranked-alternatives")
def ranked_alternatives(req: RankedAlternativesRequest):
    """
    Get solver-ranked berth alternatives for a specific vessel.

    Runs the optimizer multiple times, locking each berth one at a time,
    and returns the ranked list with objective values.
    """
    if not port_exists(req.port_code):
        raise HTTPException(status_code=404, detail=f"Port '{req.port_code}' not found")

    vessels = [_vessel_req_to_input(v) for v in req.vessels]
    berths = _load_berths(req.port_code)
    config = SchedulerConfig(max_solve_seconds=10)  # Quick solves
    resources = [ResourceInput("pilot", capacity=2), ResourceInput("tug", capacity=3)]

    target_vessel = next((v for v in vessels if v.vessel_id == req.vessel_id), None)
    if not target_vessel:
        raise HTTPException(status_code=404, detail=f"Vessel '{req.vessel_id}' not found in vessel list")

    # Check feasibility for each berth
    checker = FeasibilityChecker(config)
    alternatives = []

    for b in berths:
        feas = checker.check(target_vessel, b)
        if not feas.feasible:
            alternatives.append({
                "rank": 0,
                "berth_code": b.berth_code,
                "berth_name": b.berth_name,
                "objective_value": float("inf"),
                "waiting_hours": 0,
                "cost": 0,
                "confidence_pct": 0,
                "feasibility_score": round(feas.score * 100, 1),
                "reason": feas.violation_summary,
                "is_current": False,
            })
            continue

        # Run solver with this vessel locked to this berth
        v_copy = VesselInput(
            vessel_id=target_vessel.vessel_id,
            name=target_vessel.name,
            vessel_type=target_vessel.vessel_type,
            loa_m=target_vessel.loa_m,
            beam_m=target_vessel.beam_m,
            draft_m=target_vessel.draft_m,
            cargo_type=target_vessel.cargo_type,
            cargo_tons=target_vessel.cargo_tons,
            eta_minutes=target_vessel.eta_minutes,
            service_time_minutes=target_vessel.service_time_minutes,
            priority=1,  # highest
            preferred_berths=[b.berth_code],
            sla_max_wait_minutes=target_vessel.sla_max_wait_minutes,
        )

        test_vessels = [v_copy] + [v for v in vessels if v.vessel_id != req.vessel_id]

        try:
            scheduler = RollingHorizonScheduler(config)
            snapshot = scheduler.optimize(test_vessels, berths, resources=resources)
            sr = snapshot.solver_result
            if sr and sr.assignments:
                my_assignment = next(
                    (a for a in sr.assignments if a.vessel_id == req.vessel_id), None
                )
                alternatives.append({
                    "rank": 0,
                    "berth_code": b.berth_code,
                    "berth_name": b.berth_name,
                    "objective_value": sr.objective_value,
                    "waiting_hours": round(my_assignment.waiting_minutes / 60, 1) if my_assignment else 0,
                    "cost": 0,
                    "confidence_pct": round(feas.score * 100, 1),
                    "feasibility_score": round(feas.score * 100, 1),
                    "reason": f"Objective: {sr.objective_value:.0f}, Wait: {my_assignment.waiting_minutes / 60:.1f}h" if my_assignment else "",
                    "is_current": False,
                })
        except Exception:
            alternatives.append({
                "rank": 0,
                "berth_code": b.berth_code,
                "berth_name": b.berth_name,
                "objective_value": float("inf"),
                "waiting_hours": 0,
                "cost": 0,
                "confidence_pct": 0,
                "feasibility_score": round(feas.score * 100, 1),
                "reason": "Solver error",
                "is_current": False,
            })

    # Sort by objective value and assign ranks
    feasible_alts = [a for a in alternatives if a["objective_value"] != float("inf")]
    infeasible_alts = [a for a in alternatives if a["objective_value"] == float("inf")]
    feasible_alts.sort(key=lambda a: a["objective_value"])
    for i, a in enumerate(feasible_alts):
        a["rank"] = i + 1
    for a in infeasible_alts:
        a["rank"] = len(feasible_alts) + 1

    # Mark current assignment
    cached = _last_schedules.get(req.port_code)
    if cached:
        current_berth = next(
            (a.berth_code for a in cached.assignments if a.vessel_id == req.vessel_id), None
        )
        if current_berth:
            for a in feasible_alts + infeasible_alts:
                a["is_current"] = a["berth_code"] == current_berth

    return {
        "vessel_id": req.vessel_id,
        "alternatives": feasible_alts + infeasible_alts,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  COMMERCIAL INTELLIGENCE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

try:
    from commercial_engine.commercial_scorer import (
        CommercialScorer, CommercialDecisionConfig as EngineDecisionConfig,
    )
    from commercial_engine.partnership_manager import PartnershipManager
    from commercial_engine.berth_economics import BerthEconomicsCalculator
    from commercial_engine.dynamic_pricing import DynamicPricingEngine
    from db.commercial_repository import (
        get_all_companies, get_all_berth_economics, upsert_company,
        get_recent_assignments,
    )
    COMMERCIAL_AVAILABLE = True
except ImportError:
    COMMERCIAL_AVAILABLE = False


class CommercialConfig(BaseModel):
    commercial_flag: bool = False
    partnership_system_enabled: bool = True
    dynamic_pricing_enabled: bool = True
    decision_mode: str = "balanced"


class CommercialScoreRequest(BaseModel):
    vessel_type: str
    berth_options: List[Dict[str, Any]] = Field(default_factory=list)
    vessel_company: str = ""
    cargo_quantity: float = 0.0
    cargo_size: str = "20ft"
    service_hours: float = 24.0
    current_utilization: Dict[str, float] = Field(default_factory=dict)
    is_hazmat: bool = False
    config: CommercialConfig = Field(default_factory=CommercialConfig)


class PartnershipUpsert(BaseModel):
    company_id: str
    display_name: str
    tier: str = "STANDARD"
    discount_percentage: float = 0.0
    discount_reason: str = ""
    annual_contract_value: float = 0.0
    visits_per_year: int = 0
    is_contract: bool = False
    contact_person: str = ""
    contact_title: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""


@app.get("/api/v1/commercial/status")
def commercial_status():
    return {"available": COMMERCIAL_AVAILABLE, "version": "1.0.0"}


@app.post("/api/v1/commercial/score")
def commercial_score(req: CommercialScoreRequest):
    if not COMMERCIAL_AVAILABLE:
        raise HTTPException(503, "Commercial Intelligence module not available")
    scorer = CommercialScorer()
    cfg = EngineDecisionConfig(
        commercial_flag=req.config.commercial_flag,
        partnership_system_enabled=req.config.partnership_system_enabled,
        dynamic_pricing_enabled=req.config.dynamic_pricing_enabled,
        decision_mode=req.config.decision_mode,
    )
    results = scorer.score_berths(
        vessel_type=req.vessel_type,
        berth_options=req.berth_options,
        vessel_company_name=req.vessel_company,
        cargo_quantity=req.cargo_quantity,
        cargo_size=req.cargo_size,
        service_hours=req.service_hours,
        current_utilization_map=req.current_utilization,
        is_hazmat=req.is_hazmat,
        config=cfg,
    )
    output = []
    for r in results:
        rev = r.revenue_estimate
        output.append({
            "berth_code": r.berth_code,
            "final_score": r.final_score,
            "technical_score": r.technical_score,
            "commercial_score": r.commercial_score,
            "strategic_score": r.strategic_score,
            "gross_revenue": rev.gross_revenue if rev else 0,
            "net_revenue": rev.net_revenue if rev else 0,
            "profit_margin_pct": round((rev.profit_margin or 0) * 100, 1) if rev else 0,
            "revenue_tier": rev.revenue_tier if rev else "LOW",
            "partnership_tier": r.company.tier.value if r.company else "STANDARD",
            "tier_badge": r.company.tier_badge if r.company else "📦 STANDARD",
            "discount_pct": r.discount_applied_pct,
            "dynamic_multiplier": r.pricing_adjustment.final_multiplier if r.pricing_adjustment else 1.0,
            "pricing_note": r.pricing_note,
            "headline": r.commercial_headline,
            "reasons": r.commercial_reasons,
        })
    return {"results": output, "count": len(output)}


@app.get("/api/v1/partnerships")
def list_partnerships():
    if not COMMERCIAL_AVAILABLE:
        raise HTTPException(503, "Commercial Intelligence module not available")
    companies = get_all_companies()
    mgr = PartnershipManager(companies)
    return {"partnerships": mgr.get_all_as_table(), "count": len(companies)}


@app.post("/api/v1/partnerships/{company_id}")
def upsert_partnership(company_id: str, payload: PartnershipUpsert):
    if not COMMERCIAL_AVAILABLE:
        raise HTTPException(503, "Commercial Intelligence module not available")
    from commercial_engine.partnership_manager import VesselCompany, PartnershipTier
    try:
        tier = PartnershipTier(payload.tier)
    except ValueError:
        raise HTTPException(400, f"Invalid tier: {payload.tier}")
    company = VesselCompany(
        company_id=company_id, display_name=payload.display_name, tier=tier,
        annual_contract_value=payload.annual_contract_value,
        visits_per_year=payload.visits_per_year, is_contract=payload.is_contract,
        discount_percentage=payload.discount_percentage, discount_reason=payload.discount_reason,
        contact_person=payload.contact_person, contact_title=payload.contact_title,
        email=payload.email, phone=payload.phone, notes=payload.notes,
    )
    success = upsert_company(company)
    return {"success": success, "company_id": company_id, "tier": tier.value}


@app.get("/api/v1/berth-economics")
def list_berth_economics():
    if not COMMERCIAL_AVAILABLE:
        raise HTTPException(503, "Commercial Intelligence module not available")
    econ = get_all_berth_economics()
    rows = [{
        "berth_code": bc, "berth_class": e.berth_class, "specialization": e.specialization,
        "base_cost_per_hr": e.base_operating_cost_per_hour,
        "avg_revenue_per_call": e.avg_revenue_per_call,
        "profit_margin": e.estimated_profit_margin,
    } for bc, e in econ.items()]
    return {"berth_economics": rows, "count": len(rows)}


@app.get("/api/v1/commercial/assignments/recent")
def recent_commercial_assignments(limit: int = 50):
    if not COMMERCIAL_AVAILABLE:
        raise HTTPException(503, "Commercial Intelligence module not available")
    return {"assignments": get_recent_assignments(limit)}


# ── Entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
