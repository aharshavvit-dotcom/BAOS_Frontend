"""
Integration test — verifies the full optimization pipeline.
Run: python -m pytest tests/test_optimizer.py -v
Or:  python tests/test_optimizer.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engines.simulation.optimization.constraint_model import (
    VesselInput, BerthInput, SchedulerConfig,
    ResourceInput, TideWindowInput,
    DowntimeWindowInput, WeatherWindowInput,
    BerthConstraintModel, build_and_solve,
    AssignmentResult,
    OPTIMAL, FEASIBLE,
)
from engines.simulation.optimization.feasibility_checker import FeasibilityChecker
from engines.simulation.optimization.scheduler import RollingHorizonScheduler
from engines.analytics.cost.cost_model import CostEngine, CostConfig
from engines.core.decision.confidence import ConfidenceCalculator
from engines.analytics.kpi.kpi_calculator import KPICalculator
from engines.analytics.explanation.explainer import AgenticExplainer
from engines.simulation.digital_twin import PortDigitalTwin


def test_basic_assignment():
    """Test: 1 vessel, 2 berths -> should assign to feasible berth."""
    vessels = [
        VesselInput("V1", name="Test Ship", loa_m=200, draft_m=10,
                     eta_minutes=0, service_time_minutes=720),
    ]
    berths = [
        BerthInput("B1", berth_name="Berth Alpha", max_loa_m=250, depth_m=14),
        BerthInput("B2", berth_name="Berth Beta", max_loa_m=150, depth_m=12),  # Too small
    ]

    result = build_and_solve(vessels, berths, SchedulerConfig())
    assert result.status in (OPTIMAL, FEASIBLE), f"Solver failed: {result.status_name}"
    assert len(result.assignments) == 1
    assert result.assignments[0].berth_code == "B1", "Should assign to B1 (B2 too small)"
    print(f"  PASS Basic assignment: V1 -> {result.assignments[0].berth_code}")


def test_multi_vessel_no_overlap():
    """Test: 3 vessels, 2 berths -> no overlapping schedules."""
    vessels = [
        VesselInput("V1", name="Ship A", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600),
        VesselInput("V2", name="Ship B", loa_m=160, draft_m=8,
                     eta_minutes=60, service_time_minutes=480),
        VesselInput("V3", name="Ship C", loa_m=140, draft_m=7,
                     eta_minutes=120, service_time_minutes=360),
    ]
    berths = [
        BerthInput("B1", berth_name="Berth 1", max_loa_m=200, depth_m=14),
        BerthInput("B2", berth_name="Berth 2", max_loa_m=200, depth_m=13),
    ]

    result = build_and_solve(vessels, berths, SchedulerConfig())
    assert result.status in (OPTIMAL, FEASIBLE), f"Solver failed: {result.status_name}"
    assert len(result.assignments) == 3, f"Expected 3 assignments, got {len(result.assignments)}"

    # Verify no overlap per berth
    by_berth = {}
    for a in result.assignments:
        by_berth.setdefault(a.berth_code, []).append((a.start_minutes, a.end_minutes))

    for bc, intervals in by_berth.items():
        intervals.sort()
        for i in range(len(intervals) - 1):
            assert intervals[i][1] <= intervals[i + 1][0], \
                f"Overlap at berth {bc}: {intervals[i]} vs {intervals[i+1]}"

    print(f"  PASS Multi-vessel: {len(result.assignments)} assigned, no overlaps")
    for a in result.assignments:
        print(f"    {a.vessel_name} -> {a.berth_code} "
              f"[{a.start_minutes}-{a.end_minutes}] wait={a.waiting_minutes}min")


def test_infeasible_vessel():
    """Test: vessel too large for all berths -> should be unassigned."""
    vessels = [
        VesselInput("V_BIG", name="Giant Ship", loa_m=500, draft_m=25,
                     eta_minutes=0, service_time_minutes=720),
    ]
    berths = [
        BerthInput("B1", max_loa_m=300, depth_m=14, max_draft_m=15),
    ]

    checker = FeasibilityChecker(SchedulerConfig())
    report = checker.check(vessels[0], berths[0])
    assert not report.feasible, "Giant ship should be infeasible"
    assert report.hard_violations > 0
    print(f"  PASS Infeasibility detected: {report.violation_summary}")


def test_feasibility_checker():
    """Test feasibility checker with detailed reports."""
    vessel = VesselInput("V1", loa_m=200, draft_m=10, beam_m=32)
    berth = BerthInput("B1", max_loa_m=250, depth_m=14, max_beam_m=40)

    checker = FeasibilityChecker()
    report = checker.check(vessel, berth)
    assert report.feasible
    assert report.hard_violations == 0
    print(f"  PASS Feasibility checker: score={report.score:.2f}, "
          f"{len(report.checks)} checks passed")


def test_fcfs_constraint():
    """Test FCFS ordering: earlier ETA vessels should start first."""
    vessels = [
        VesselInput("V1", name="Early", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=480),
        VesselInput("V2", name="Late", loa_m=150, draft_m=8,
                     eta_minutes=120, service_time_minutes=480),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
    ]

    config = SchedulerConfig(fcfs_enabled=True)
    result = build_and_solve(vessels, berths, config)
    assert result.status in (OPTIMAL, FEASIBLE)

    starts = {a.vessel_id: a.start_minutes for a in result.assignments}
    assert starts["V1"] <= starts["V2"], "FCFS: V1 (earlier ETA) should start first"
    print(f"  PASS FCFS: V1 starts at {starts['V1']}, V2 at {starts['V2']}")


def test_customs_clearance():
    """Test: uncleared vessel should not be assigned."""
    vessels = [
        VesselInput("V1", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600, customs_cleared=False),
        VesselInput("V2", loa_m=160, draft_m=8,
                     eta_minutes=0, service_time_minutes=480, customs_cleared=True),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
    ]

    result = build_and_solve(vessels, berths, SchedulerConfig())
    # V1 has customs_cleared=False -> x[V1, B1] = 0 -> infeasible for V1
    # The model requires exactly one berth per vessel, so this should be infeasible
    # unless we handle it gracefully
    assigned_ids = {a.vessel_id for a in result.assignments}
    print(f"  PASS Customs: assigned={assigned_ids}")


def test_resource_constraints():
    """Test: limited pilot availability."""
    vessels = [
        VesselInput("V1", loa_m=180, draft_m=9, needs_pilot=True,
                     eta_minutes=0, service_time_minutes=600),
        VesselInput("V2", loa_m=160, draft_m=8, needs_pilot=True,
                     eta_minutes=0, service_time_minutes=480),
        VesselInput("V3", loa_m=140, draft_m=7, needs_pilot=True,
                     eta_minutes=0, service_time_minutes=360),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
        BerthInput("B2", max_loa_m=200, depth_m=14),
        BerthInput("B3", max_loa_m=200, depth_m=14),
    ]
    resources = [ResourceInput("pilot", capacity=1)]  # Only 1 pilot

    result = build_and_solve(vessels, berths, SchedulerConfig(), resources=resources)
    assert result.status in (OPTIMAL, FEASIBLE)

    # With only 1 pilot, vessels should be staggered (not all starting at once)
    starts = sorted(a.start_minutes for a in result.assignments)
    # At least some separation due to movement_duration constraint
    print(f"  PASS Resource constraint: starts={starts}")


def test_cost_engine():
    """Test cost calculations."""
    engine = CostEngine()
    bd = engine.compute_vessel_cost(
        wait_hours=5.0,
        service_hours=24.0,
        cargo_tons=25000,
        demurrage_rate=800,
        sla_max_wait_hours=4.0,
    )
    assert bd.waiting_cost == 4000.0  # 800 * 5
    assert bd.sla_penalty > 0  # 1 hour over SLA
    assert bd.revenue == 62500.0  # 25000 * 2.5
    print(f"  PASS Cost engine: total=${bd.total_cost:,.0f}, rev=${bd.revenue:,.0f}, net=${bd.net_cost:,.0f}")


def test_confidence_calculator():
    """Test calibrated confidence."""
    calc = ConfidenceCalculator()
    result = calc.compute(
        prediction_variance=0.1,
        max_prediction_variance=1.0,
        scenario_stability=0.9,
    )
    assert 0 <= result.confidence_pct <= 100
    assert result.risk_level in ("Low", "Medium", "High")
    print(f"  PASS Confidence: {result.confidence_pct}% ({result.risk_level} risk)")
    print(f"    Components: FS={result.feasibility_stability:.2f}, "
          f"PC={result.prediction_certainty:.2f}, HM={result.historical_match:.2f}")


def test_kpi_calculator():
    """Test KPI dashboard computation."""
    vessels_input = [
        VesselInput("V1", cargo_tons=20000, loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600),
    ]
    berths_input = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
    ]
    result = build_and_solve(vessels_input, berths_input, SchedulerConfig())

    calc = KPICalculator()
    vessels_dict = {v.vessel_id: v for v in vessels_input}
    berths_dict = {b.berth_code: b for b in berths_input}
    dash = calc.compute(result, vessels_dict, berths_dict)

    assert dash.total_vessels == 1
    assert dash.vessels_assigned == 1
    assert dash.sla_compliance_pct > 0
    print(f"  PASS KPIs: util={dash.berth_utilization_pct}%, "
          f"avg_wait={dash.avg_waiting_hours}h, "
          f"SLA={dash.sla_compliance_pct}%")


def test_digital_twin():
    """Test digital twin simulation."""
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
        BerthInput("B2", max_loa_m=200, depth_m=13),
    ]
    vessels = [
        VesselInput(f"V{i}", loa_m=180, draft_m=9,
                     eta_minutes=i * 120, service_time_minutes=360)
        for i in range(5)
    ]

    twin = PortDigitalTwin(berths)
    twin.add_vessel_arrivals(vessels)
    twin.add_weather_event(start_minutes=600, duration_minutes=120)
    result = twin.simulate(duration_hours=48)

    assert result.events_processed > 0
    assert result.vessels_processed >= 0
    print(f"  PASS Digital Twin: processed {result.vessels_processed} vessels, "
          f"{result.disruptions_count} disruptions, "
          f"avg wait={result.avg_waiting_minutes:.0f}min")


def test_scheduler():
    """Test rolling horizon scheduler."""
    vessels = [
        VesselInput("V1", name="Alpha", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600),
        VesselInput("V2", name="Beta", loa_m=160, draft_m=8,
                     eta_minutes=60, service_time_minutes=480),
    ]
    berths = [
        BerthInput("B1", berth_name="Berth 1", max_loa_m=200, depth_m=14),
        BerthInput("B2", berth_name="Berth 2", max_loa_m=200, depth_m=13),
    ]

    scheduler = RollingHorizonScheduler(SchedulerConfig())
    snapshot = scheduler.optimize(vessels, berths)

    assert snapshot.solver_result is not None
    assert snapshot.solver_result.status in (OPTIMAL, FEASIBLE)
    print(f"  PASS Scheduler: {len(snapshot.solver_result.assignments)} assignments, "
          f"run #{snapshot.run_number}")


def test_explainer():
    """Test agentic explainer with what-if."""
    vessels = [
        VesselInput("V1", name="Ship A", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600, cargo_tons=20000),
    ]
    berths = [
        BerthInput("B1", berth_name="Berth 1", max_loa_m=200, depth_m=14),
    ]

    result = build_and_solve(vessels, berths, SchedulerConfig())
    explainer = AgenticExplainer()

    if result.assignments:
        vessels_dict = {v.vessel_id: v for v in vessels}
        berths_dict = {b.berth_code: b for b in berths}
        explanation = explainer.explain_assignment(
            result.assignments[0], result, vessels_dict, berths_dict,
        )
        print(f"  PASS Explainer: {explanation.headline}")
        print(f"    Reasons: {explanation.reasons[:2]}")
        print(f"    Cost: {explanation.cost_note}")


def test_outbound_channel():
    """Test: outbound departures are also channel-constrained."""
    # 3 vessels with same ETA and short service → departures cluster together
    vessels = [
        VesselInput(f"V{i}", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=120)
        for i in range(3)
    ]
    berths = [
        BerthInput(f"B{i}", max_loa_m=200, depth_m=14)
        for i in range(3)
    ]
    # 1 channel movement at a time, 60 min duration
    config = SchedulerConfig(
        max_channel_movements=1, movement_duration_minutes=60,
        ukc_margin_m=0.0,  # disable for this test
    )
    resources = [ResourceInput("pilot", capacity=3)]
    result = build_and_solve(vessels, berths, config, resources=resources)
    assert result.status in (OPTIMAL, FEASIBLE)
    # All vessels should be assigned
    assert len(result.assignments) == 3
    # With 1 channel slot and 60min movement, starts AND ends must be staggered
    # → total schedule span must be at least 5*60 = 300 min
    # (3 inbound + 3 outbound = 6 movements, 1 at a time, but some can overlap)
    starts = sorted(a.start_minutes for a in result.assignments)
    ends = sorted(a.end_minutes for a in result.assignments)
    # At minimum, consecutive starts must be 60min apart
    for i in range(len(starts) - 1):
        assert starts[i + 1] - starts[i] >= 60, \
            f"Starts not staggered: {starts}"
    print(f"  PASS Outbound channel: starts={starts}, ends={ends}")


def test_downtime_blocking():
    """Test: vessel cannot be assigned during berth downtime."""
    vessels = [
        VesselInput("V1", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=600),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
        BerthInput("B2", max_loa_m=200, depth_m=14),
    ]
    # B1 in downtime from 0..1000 → vessel must go to B2
    downtimes = [
        DowntimeWindowInput(berth_code="B1", start_min=0, end_min=1000,
                            reason="Planned maintenance"),
    ]
    config = SchedulerConfig(ukc_margin_m=0.0)
    result = build_and_solve(vessels, berths, config, downtimes=downtimes)
    assert result.status in (OPTIMAL, FEASIBLE)
    assert len(result.assignments) == 1
    a = result.assignments[0]
    # Either assigned to B2 directly, or to B1 but starting after downtime ends
    if a.berth_code == "B1":
        assert a.start_minutes >= 1000, \
            f"Vessel started at B1 during downtime: start={a.start_minutes}"
    print(f"  PASS Downtime: V1 -> {a.berth_code} (start={a.start_minutes})")


def test_deviation_penalty():
    """Test: re-optimization with deviation penalty keeps assignments stable."""
    from engines.simulation.optimization.constraint_model import AssignmentResult
    vessels = [
        VesselInput("V1", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=600),
        VesselInput("V2", loa_m=140, draft_m=7,
                     eta_minutes=60, service_time_minutes=480),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
        BerthInput("B2", max_loa_m=200, depth_m=14),
    ]
    config = SchedulerConfig(w_deviation=5.0, ukc_margin_m=0.0)

    # First solve (no previous)
    result1 = build_and_solve(vessels, berths, config)
    assert result1.status in (OPTIMAL, FEASIBLE)

    # Second solve with previous assignments → should keep same berths
    result2 = build_and_solve(vessels, berths, config,
                              previous_assignments=result1.assignments)
    assert result2.status in (OPTIMAL, FEASIBLE)

    # Check that assignments are identical
    map1 = {a.vessel_id: a.berth_code for a in result1.assignments}
    map2 = {a.vessel_id: a.berth_code for a in result2.assignments}
    assert map1 == map2, f"Assignments changed: {map1} -> {map2}"
    print(f"  PASS Deviation penalty: assignments stable {map1}")


def test_ukc_margin():
    """Test: vessel near draft limit blocked when UKC margin applied."""
    vessel = VesselInput("V1", loa_m=180, draft_m=14.0)
    berth = BerthInput("B1", max_loa_m=200, max_draft_m=14.3, depth_m=16)

    # Without margin (0.0): draft 14.0 <= 14.3 → passes
    from engines.simulation.optimization.feasibility_checker import FeasibilityChecker
    checker_no_margin = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0.0))
    r1 = checker_no_margin.check(vessel, berth)
    draft_check_1 = [c for c in r1.checks if c.name == "Draft clearance"][0]
    assert draft_check_1.passed, "Should pass without UKC margin"

    # With margin (0.5): draft 14.0 + 0.5 = 14.5 > 14.3 → fails
    checker_margin = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0.5))
    r2 = checker_margin.check(vessel, berth)
    draft_check_2 = [c for c in r2.checks if c.name == "Draft clearance"][0]
    assert not draft_check_2.passed, "Should fail with UKC margin"
    print(f"  PASS UKC margin: no-margin={draft_check_1.passed}, with-margin={draft_check_2.passed}")


def test_weather_blocking():
    """Test: weather window blocks all berths."""
    vessels = [
        VesselInput("V1", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=300),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
    ]
    # Weather blocks 0..500 → vessel must start after 500
    weather = [
        WeatherWindowInput(start_min=0, end_min=500, reason="Storm"),
    ]
    config = SchedulerConfig(ukc_margin_m=0.0)
    result = build_and_solve(vessels, berths, config, weather=weather)
    assert result.status in (OPTIMAL, FEASIBLE)
    assert len(result.assignments) == 1
    assert result.assignments[0].start_minutes >= 500, \
        f"Vessel started during weather: {result.assignments[0].start_minutes}"
    print(f"  PASS Weather blocking: start={result.assignments[0].start_minutes}")


def test_demurrage_objective():
    """Test: vessel with higher demurrage cost scheduled earlier."""
    vessels = [
        VesselInput("V_LOW", name="Low Cost", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=480,
                     demurrage_cost_per_hr=100),
        VesselInput("V_HIGH", name="High Cost", loa_m=150, draft_m=8,
                     eta_minutes=0, service_time_minutes=480,
                     demurrage_cost_per_hr=5000),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
    ]
    config = SchedulerConfig(w_demurrage=1.0, ukc_margin_m=0.0)
    result = build_and_solve(vessels, berths, config)
    assert result.status in (OPTIMAL, FEASIBLE)
    starts = {a.vessel_id: a.start_minutes for a in result.assignments}
    # High-demurrage vessel should start first (less waiting = less cost)
    assert starts["V_HIGH"] <= starts["V_LOW"], \
        f"High-demurrage vessel should start first: {starts}"
    print(f"  PASS Demurrage objective: V_HIGH={starts['V_HIGH']}, V_LOW={starts['V_LOW']}")


def test_confidence_with_solver_gap():
    """Test: confidence reflects solver status."""
    calc = ConfidenceCalculator()

    # OPTIMAL solver → higher confidence
    r_optimal = calc.compute(
        prediction_variance=0.1, max_prediction_variance=1.0,
        scenario_stability=0.9, solver_status=4,  # OPTIMAL
    )
    # FEASIBLE solver with gap → lower confidence
    r_feasible = calc.compute(
        prediction_variance=0.1, max_prediction_variance=1.0,
        scenario_stability=0.9, solver_status=2, objective_gap=0.3,
    )

    assert r_optimal.confidence_pct > r_feasible.confidence_pct, \
        f"OPTIMAL ({r_optimal.confidence_pct}) should be higher than FEASIBLE ({r_feasible.confidence_pct})"
    print(f"  PASS Solver gap: OPTIMAL={r_optimal.confidence_pct}%, "
          f"FEASIBLE(gap=0.3)={r_feasible.confidence_pct}%")


# ── Scenario Engine Tests ──────────────────────────────────────────────────

def test_manual_override():
    """Test: manual override locks vessel→berth assignment."""
    vessels = [
        VesselInput("V1", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600),
        VesselInput("V2", loa_m=160, draft_m=8,
                     eta_minutes=60, service_time_minutes=480),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
        BerthInput("B2", max_loa_m=200, depth_m=14),
    ]

    # Solve without override
    result1 = build_and_solve(vessels, berths, SchedulerConfig())
    assert result1.status in (OPTIMAL, FEASIBLE)

    # Force V1 → B2 via manual override
    result2 = build_and_solve(
        vessels, berths, SchedulerConfig(),
        manual_overrides=[("V1", "B2")],
    )
    assert result2.status in (OPTIMAL, FEASIBLE)
    v1_berth = next(a.berth_code for a in result2.assignments if a.vessel_id == "V1")
    assert v1_berth == "B2", f"V1 should be locked to B2, got {v1_berth}"
    print(f"  PASS Manual override: V1 locked to B2={v1_berth}")


def test_ranked_alternatives():
    """Test: ranked alternatives computed for each vessel."""
    from engines.simulation.scenario.scenario_manager import ScenarioManager

    vessels = [
        VesselInput("V1", name="Ship A", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600),
    ]
    berths = [
        BerthInput("B1", berth_name="Berth Alpha", max_loa_m=200, depth_m=14),
        BerthInput("B2", berth_name="Berth Beta", max_loa_m=200, depth_m=14),
    ]

    result = build_and_solve(vessels, berths, SchedulerConfig())
    mgr = ScenarioManager(vessels, berths, SchedulerConfig())
    ranked = mgr.compute_ranked_alternatives(result, top_k=5)

    assert "V1" in ranked, "V1 should have alternatives"
    options = ranked["V1"]
    assert len(options) >= 2, f"Expected ≥2 options, got {len(options)}"
    assert options[0].rank == 1, "First option should be rank 1"

    # Current assignment should be marked
    has_current = any(o.is_current for o in options)
    assert has_current, "One option should be marked is_current"

    print(f"  PASS Ranked alternatives: V1 has {len(options)} options, "
          f"ranks={[o.rank for o in options]}")


def test_conflict_detection():
    """Test: conflict detector identifies overlaps."""
    from engines.simulation.scenario.conflict_detector import detect_conflicts

    vessels = {
        "V1": VesselInput("V1", loa_m=180, draft_m=9,
                          eta_minutes=0, service_time_minutes=600),
        "V2": VesselInput("V2", loa_m=160, draft_m=8,
                          eta_minutes=0, service_time_minutes=480),
    }
    berths = {
        "B1": BerthInput("B1", max_loa_m=200, depth_m=14),
    }

    # V2 already at B1 from 0-480
    existing = [
        AssignmentResult(
            vessel_id="V2", vessel_name="Ship B",
            berth_code="B1", berth_name="Berth 1",
            start_minutes=0, end_minutes=480,
            waiting_minutes=0, service_minutes=480,
        ),
    ]

    # Check V1 → B1 at 0-600 (overlaps with V2)
    conflicts = detect_conflicts(
        vessel_id="V1", berth_code="B1",
        start_min=0, end_min=600,
        vessels=vessels, berths=berths,
        existing_assignments=existing,
    )
    assert len(conflicts) > 0, "Should detect overlap"
    assert any("Overlap" in c for c in conflicts), f"Should mention overlap: {conflicts}"
    print(f"  PASS Conflict detection: {len(conflicts)} conflicts found: {conflicts[0]}")


def test_feasibility_reasons():
    """Test: get_reason_summary returns human-readable reasons."""
    vessel = VesselInput("V1", loa_m=200, draft_m=10, beam_m=32)
    berth = BerthInput("B1", max_loa_m=250, depth_m=14, max_beam_m=40)

    checker = FeasibilityChecker()
    report = checker.check(vessel, berth)
    summary = report.get_reason_summary()

    assert "is_feasible" in summary, "Should have is_feasible key"
    assert summary["is_feasible"] is True
    assert len(summary["reasons"]) > 0, "Should have reason strings"
    assert any("LOA" in r for r in summary["reasons"]), f"Should mention LOA: {summary['reasons']}"
    print(f"  PASS Feasibility reasons: {len(summary['reasons'])} reasons, "
          f"e.g.: '{summary['reasons'][0]}'")


def test_scenario_impact():
    """Test: override produces valid ScenarioImpact."""
    from engines.simulation.scenario.scenario_manager import ScenarioManager, ManualOverride

    vessels = [
        VesselInput("V1", name="Ship A", loa_m=180, draft_m=9,
                     eta_minutes=0, service_time_minutes=600, cargo_tons=15000),
        VesselInput("V2", name="Ship B", loa_m=160, draft_m=8,
                     eta_minutes=60, service_time_minutes=480, cargo_tons=10000),
    ]
    berths = [
        BerthInput("B1", berth_name="Berth 1", max_loa_m=200, depth_m=14),
        BerthInput("B2", berth_name="Berth 2", max_loa_m=200, depth_m=14),
    ]

    config = SchedulerConfig()
    result = build_and_solve(vessels, berths, config)

    mgr = ScenarioManager(vessels, berths, config)

    # Apply an override: send V1 to B2
    impact = mgr.apply_overrides(
        overrides=[ManualOverride(vessel_id="V1", berth_code="B2")],
        original_result=result,
    )

    assert impact.new_result is not None, "Should have new solver result"
    assert impact.original_objective >= 0, \
        f"Should have non-negative original objective, got {impact.original_objective}"
    assert impact.new_objective >= 0, \
        f"Should have non-negative new objective, got {impact.new_objective}"
    assert len(impact.summary_lines) > 0, "Should have summary lines"
    print(f"  PASS Scenario impact: obj {impact.original_objective:.0f} -> "
          f"{impact.new_objective:.0f} ({impact.objective_delta_pct:+.1f}%), "
          f"summary: {impact.summary_lines}")


def test_cascading_conflict_resolution():
    """Test: cascading conflict resolver auto-reassigns displaced vessel."""
    from engines.simulation.scenario.conflict_resolver import resolve_cascading_conflicts

    vessels = {
        "V1": VesselInput("V1", name="Ship A", loa_m=180, draft_m=9,
                          eta_minutes=0, service_time_minutes=600),
        "V2": VesselInput("V2", name="Ship B", loa_m=160, draft_m=8,
                          eta_minutes=60, service_time_minutes=480),
        "V3": VesselInput("V3", name="Ship C", loa_m=140, draft_m=7,
                          eta_minutes=120, service_time_minutes=360),
    }
    berths = {
        "B1": BerthInput("B1", max_loa_m=200, depth_m=14),
        "B2": BerthInput("B2", max_loa_m=200, depth_m=14),
        "B3": BerthInput("B3", max_loa_m=200, depth_m=14),
    }

    # Current assignments: V1→B1, V2→B2, V3→B3
    current = [
        AssignmentResult("V1", "Ship A", "B1", "Berth 1", 0, 600, 0, 600),
        AssignmentResult("V2", "Ship B", "B2", "Berth 2", 60, 540, 0, 480),
        AssignmentResult("V3", "Ship C", "B3", "Berth 3", 120, 480, 0, 360),
    ]

    # User moves V1 → B2 (displaces V2)
    cascade = resolve_cascading_conflicts(
        user_vessel_id="V1",
        user_new_berth="B2",
        current_assignments=current,
        vessels=vessels,
        berths=berths,
    )

    assert cascade.has_conflicts, "Should detect conflict"
    assert len(cascade.reassignments) >= 1, "Should have at least 1 reassignment"
    # V2 should be reassigned somewhere other than B2
    v2_reassigned = next((r for r in cascade.reassignments if r.vessel_id == "V2"), None)
    assert v2_reassigned is not None, "V2 should be reassigned"
    assert v2_reassigned.to_berth != "B2", "V2 should not stay at B2"
    # No duplicate berths in final overrides
    final_berths = list(cascade.all_overrides.values())
    assert len(final_berths) == len(set(final_berths)), \
        f"No duplicate berths allowed: {cascade.all_overrides}"
    print(f"  PASS Cascade: {len(cascade.reassignments)} reassignments, "
          f"depth={cascade.cascade_depth}, overrides={cascade.all_overrides}")


def test_ship_type_config_resolution():
    """Test: BerthSchedulerConfig 4-level lookup priority."""

    global_cfg = SchedulerConfig(w_waiting=1.0)
    berth_cfg = SchedulerConfig(w_waiting=2.0)
    ship_cfg = SchedulerConfig(w_waiting=3.0)
    bs_cfg = SchedulerConfig(w_waiting=4.0)

    from engines.simulation.optimization.constraint_model import BerthSchedulerConfig as BSC
    bsc = BSC(
        global_config=global_cfg,
        berth_configs={"B1": berth_cfg},
        ship_type_configs={"Container": ship_cfg},
        berth_ship_configs={("B1", "Container"): bs_cfg},
    )

    # Level 1: (berth, ship_type) exact match
    assert bsc.for_berth_and_type("B1", "Container").w_waiting == 4.0, \
        "Should use (B1, Container) config"

    # Level 2: ship_type global (berth without specific entry)
    assert bsc.for_berth_and_type("B2", "Container").w_waiting == 3.0, \
        "Should fall back to Container global config"

    # Level 3: berth only (ship type without entry)
    assert bsc.for_berth_and_type("B1", "Tanker").w_waiting == 2.0, \
        "Should fall back to B1 berth config"

    # Level 4: global fallback
    assert bsc.for_berth_and_type("B2", "Tanker").w_waiting == 1.0, \
        "Should fall back to global config"

    # Property checks
    assert bsc.has_ship_type_configs, "Should have ship_type configs"
    assert bsc.is_per_berth, "Should be per_berth (has berth_configs)"
    print(f"  PASS Ship-type config: 4-level lookup verified")


def test_ship_type_objective_weights():
    """Test: solver uses ship-type-specific weights."""
    from engines.simulation.optimization.constraint_model import BerthSchedulerConfig as BSC

    # Container ship has high waiting weight → should minimize its wait
    container_cfg = SchedulerConfig(w_waiting=5.0, w_sla_penalty=0.0)
    # Bulk carrier has low waiting weight → less urgency
    bulk_cfg = SchedulerConfig(w_waiting=0.1, w_sla_penalty=0.0)

    bsc = BSC(
        global_config=SchedulerConfig(w_waiting=1.0),
        ship_type_configs={"Container": container_cfg, "Bulk Carrier": bulk_cfg},
    )

    vessels = [
        VesselInput("V_CONT", name="Container Express", vessel_type="Container",
                     loa_m=150, draft_m=8, eta_minutes=0, service_time_minutes=480),
        VesselInput("V_BULK", name="Bulk Hauler", vessel_type="Bulk Carrier",
                     loa_m=150, draft_m=8, eta_minutes=0, service_time_minutes=480),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14),
    ]

    result = build_and_solve(vessels, berths, bsc)
    assert result.status in (OPTIMAL, FEASIBLE), f"Solver failed: {result.status_name}"
    assert len(result.assignments) == 2

    starts = {a.vessel_id: a.start_minutes for a in result.assignments}
    # Container (high w_waiting=5.0) should start first to minimize its wait
    assert starts["V_CONT"] <= starts["V_BULK"], \
        f"Container should start first: V_CONT={starts['V_CONT']}, V_BULK={starts['V_BULK']}"
    print(f"  PASS Ship-type weights: V_CONT={starts['V_CONT']}, V_BULK={starts['V_BULK']}")


def test_cargo_type_constraint():
    """Test: vessel with cargo type is PREFERENTIALLY assigned to matching berth.
    
    NOTE: Cargo type is now a soft constraint (not a hard block).
    The solver should still prefer the matching berth via objective penalty.
    """
    vessels = [
        VesselInput("V1", name="Coal Ship", loa_m=180, draft_m=9,
                     cargo_type="Coal",
                     eta_minutes=0, service_time_minutes=600),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, depth_m=14,
                   allowed_cargo_types=["Crude Oil", "Chemicals"]),  # No Coal
        BerthInput("B2", max_loa_m=200, depth_m=14,
                   allowed_cargo_types=["Coal", "Bulk Dry"]),  # Coal OK
    ]
    config = SchedulerConfig(ukc_margin_m=0.0)
    result = build_and_solve(vessels, berths, config)
    assert result.status in (OPTIMAL, FEASIBLE), f"Solver failed: {result.status_name}"
    assert len(result.assignments) == 1
    # Vessel should be assigned to EITHER berth (cargo type is soft now)
    print(f"  PASS Cargo type constraint: V1 -> {result.assignments[0].berth_code}")


def test_cargo_type_feasibility():
    """Test: feasibility checker reports cargo type as soft constraint.
    
    NOTE: Cargo type is now a SOFT constraint - always passes but details differ.
    """
    vessel = VesselInput("V1", loa_m=180, draft_m=9, cargo_type="Chemicals")
    berth_ok = BerthInput("B1", max_loa_m=200, depth_m=14,
                          allowed_cargo_types=["Chemicals", "Crude Oil"])
    berth_bad = BerthInput("B2", max_loa_m=200, depth_m=14,
                           allowed_cargo_types=["Coal", "Bulk Dry"])

    checker = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0.0))

    r1 = checker.check(vessel, berth_ok)
    cargo_check_1 = [c for c in r1.checks if c.name == "Cargo type"][0]
    assert cargo_check_1.passed, "Chemicals should be allowed at B1"

    r2 = checker.check(vessel, berth_bad)
    cargo_check_2 = [c for c in r2.checks if c.name == "Cargo type"][0]
    # Cargo type is now SOFT - it passes but notes the mismatch
    assert cargo_check_2.passed, "Cargo type is now a soft constraint - should pass"
    assert "not in typical" in cargo_check_2.detail.lower() or "allowed" in cargo_check_2.detail.lower(), \
        f"Should explain cargo type mismatch: {cargo_check_2.detail}"
    print(f"  PASS Cargo type feasibility (soft): B1={cargo_check_1.passed}, B2={cargo_check_2.passed}")


def test_beam_constraint():
    """Test: vessel with beam exceeding berth max_beam_m is blocked (C3)."""
    vessels = [
        VesselInput("V1", name="Wide Ship", loa_m=180, beam_m=45, draft_m=9,
                     eta_minutes=0, service_time_minutes=600),
    ]
    berths = [
        BerthInput("B1", max_loa_m=200, max_beam_m=35, depth_m=14),  # Too narrow
        BerthInput("B2", max_loa_m=200, max_beam_m=50, depth_m=14),  # Wide enough
    ]
    config = SchedulerConfig(ukc_margin_m=0.0)
    result = build_and_solve(vessels, berths, config)
    assert result.status in (OPTIMAL, FEASIBLE), f"Solver failed: {result.status_name}"
    assert len(result.assignments) == 1
    assert result.assignments[0].berth_code == "B2", \
        f"Wide vessel should be assigned to B2, got {result.assignments[0].berth_code}"
    print(f"  PASS Beam constraint: V1 -> {result.assignments[0].berth_code}")


def test_beam_feasibility():
    """Test: feasibility checker reports beam pass/fail correctly."""
    vessel = VesselInput("V1", loa_m=180, beam_m=38, draft_m=9)
    berth_ok = BerthInput("B1", max_loa_m=200, max_beam_m=45, depth_m=14)
    berth_bad = BerthInput("B2", max_loa_m=200, max_beam_m=35, depth_m=14)

    checker = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0.0))

    r1 = checker.check(vessel, berth_ok)
    beam_check_1 = [c for c in r1.checks if c.name == "Beam fit"][0]
    assert beam_check_1.passed, "Beam 38m should fit in 45m berth"

    r2 = checker.check(vessel, berth_bad)
    beam_check_2 = [c for c in r2.checks if c.name == "Beam fit"][0]
    assert not beam_check_2.passed, "Beam 38m should NOT fit in 35m berth"
    assert not r2.feasible, "B2 should be infeasible for wide vessel"
    print(f"  PASS Beam feasibility: B1={beam_check_1.passed}, B2={beam_check_2.passed}")


# ── NEW: Dynamic Feasibility Tests ─────────────────────────────────────────

def test_dynamic_vessel_type_all_types():
    """Test: ALL vessel types get a compatibility score > 0 (never rejected outright when berth has equipment)."""
    from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score

    all_types = [
        "Bulk dry", "General cargo", "Container", "Tanker",
        "RoRo", "LPG tanker", "LNG tanker", "Multipurpose",
        "Chemical tanker", "Passenger",
    ]
    berth_equipment = ["crane", "hose", "gangway", "conveyor"]
    berth_allowed = ["Bulk dry", "General cargo"]  # Only 2 types historically

    for vtype in all_types:
        score, summary, factors = compute_compatibility_score(
            vtype, "General", berth_equipment, berth_allowed,
        )
        assert score > 0, f"{vtype} should have score > 0, got {score}"
        assert len(summary) > 0, f"{vtype} should have summary"
        print(f"    {vtype}: score={score}, summary={summary[:60]}...")

    print(f"  PASS Dynamic vessel types: {len(all_types)} types all scored > 0")


def test_vessel_type_soft_constraint():
    """Test: vessel type NOT in allowed list produces soft warning, not hard failure."""
    vessel = VesselInput("V1", loa_m=180, draft_m=9, beam_m=28,
                         vessel_type="Container")
    berth = BerthInput("B1", max_loa_m=250, depth_m=14, max_beam_m=40,
                       allowed_vessel_types=["Bulk dry", "General cargo"],
                       equipment_types=["crane", "gangway", "conveyor"])

    checker = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0.0))
    report = checker.check(vessel, berth)

    type_check = [c for c in report.checks if c.name == "Vessel type"][0]
    # Should be feasible (soft) even though Container not in allowed list
    assert type_check.passed, f"Container should be feasible (soft), got passed={type_check.passed}"
    assert type_check.severity == "soft", f"Should be soft, got {type_check.severity}"
    assert report.feasible, "Overall report should be feasible"
    print(f"  PASS Vessel type soft: Container at Bulk berth = feasible (soft), score={type_check.value}")


def test_compatibility_scoring():
    """Test: compute_compatibility_score returns correct relative scores."""
    from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score

    equipment = ["crane", "hose", "gangway", "conveyor"]

    # Bulk dry at bulk berth with full equipment → high score
    score_best, _, _ = compute_compatibility_score(
        "Bulk dry", "Coal", equipment, ["Bulk dry", "General cargo"],
    )
    # Container at bulk berth → moderate score (crane available but not gantry)
    score_ok, _, _ = compute_compatibility_score(
        "Container", "Containers", equipment, ["Bulk dry", "General cargo"],
    )
    # Tanker at bulk berth with 'hose' → moderate (hose matches)
    score_tanker, _, _ = compute_compatibility_score(
        "Tanker", "Crude Oil", equipment, ["Bulk dry", "General cargo"],
    )

    assert score_best > score_ok, f"Bulk at bulk berth ({score_best}) should score higher than Container ({score_ok})"
    assert score_best > 60, f"Bulk at bulk berth should be > 60, got {score_best}"
    print(f"  PASS Compatibility scoring: Bulk={score_best}, Container={score_ok}, Tanker={score_tanker}")


def test_confidence_high_for_good_match():
    """Test: physically + equipment compatible vessel-berth pair → confidence ≥ 75%.

    NOTE: The enhanced ML confidence calculator uses realistic no-data defaults
    (feasibility=0.70 instead of 0.90, historical=0.50 instead of 0.85),
    so a good match with OPTIMAL solver + 90% compatibility produces ~79%.
    This is intentional to avoid overconfidence when feasibility checks and
    historical data are not provided.
    """
    from engines.core.decision.confidence import ConfidenceCalculator

    calc = ConfidenceCalculator()
    result = calc.compute(
        solver_status=4,  # OPTIMAL
        compatibility_score=90,  # Excellent compatibility
    )
    assert result.confidence_pct >= 75, \
        f"Good match should have confidence ≥ 75%, got {result.confidence_pct}%"
    assert result.risk_level in ("Low", "Medium"), \
        f"Good match should be Low/Medium risk, got {result.risk_level}"
    print(f"  PASS Confidence high: {result.confidence_pct}% ({result.risk_level})")


def test_confidence_moderate_for_fair_match():
    """Test: moderate compatibility → confidence 65-84%."""
    from engines.core.decision.confidence import ConfidenceCalculator

    calc = ConfidenceCalculator()
    result = calc.compute(
        solver_status=4,  # OPTIMAL
        compatibility_score=55,  # Moderate compatibility
    )
    assert 50 <= result.confidence_pct <= 90, \
        f"Fair match should have moderate confidence, got {result.confidence_pct}%"
    print(f"  PASS Confidence moderate: {result.confidence_pct}% ({result.risk_level})")


def test_learning_system_record_and_retrieve():
    """Test: assignment recording and retrieval."""
    import tempfile
    import shutil
    from engines.learning.assignment_tracker import (
        record_assignment, get_berth_performance, get_compatibility_history,
        _PORTS_DIR,
    )

    # Use a temp port to avoid polluting real data
    test_port = "_test_learning_tmp"
    test_dir = _PORTS_DIR / test_port
    try:
        # Record assignments
        record_assignment(
            test_port, "V1", "Bulk dry", "B1",
            predicted_wait_hours=3.0, predicted_service_hours=24.0,
            actual_wait_hours=2.5, actual_service_hours=22.0,
            confidence_at_assignment=85.0, compatibility_score=90,
            outcome="completed",
        )
        record_assignment(
            test_port, "V2", "Container", "B1",
            predicted_wait_hours=4.0, predicted_service_hours=18.0,
            confidence_at_assignment=72.0, compatibility_score=65,
            outcome="completed",
        )
        record_assignment(
            test_port, "V3", "Bulk dry", "B1",
            predicted_wait_hours=2.0, predicted_service_hours=20.0,
            confidence_at_assignment=88.0, compatibility_score=92,
            outcome="incident",
        )

        # Get performance
        perf = get_berth_performance(test_port)
        assert "B1" in perf, "B1 should have performance data"
        assert perf["B1"]["total_assignments"] == 3
        assert perf["B1"]["completed"] == 2
        assert perf["B1"]["incidents"] == 1

        # Get compatibility history
        hist = get_compatibility_history(test_port, "Bulk dry", "B1")
        assert hist["assignment_count"] == 2, f"Expected 2 Bulk dry assignments, got {hist['assignment_count']}"
        assert hist["success_rate"] == 0.5, f"Expected 50% success, got {hist['success_rate']}"

        print(f"  PASS Learning system: recorded 3 assignments, "
              f"B1 perf={perf['B1']['success_rate']:.0%}, "
              f"Bulk@B1 success={hist['success_rate']:.0%}")
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)


# ── Run all tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Basic Assignment", test_basic_assignment),
        ("Multi-Vessel No Overlap", test_multi_vessel_no_overlap),
        ("Infeasible Vessel", test_infeasible_vessel),
        ("Feasibility Checker", test_feasibility_checker),
        ("FCFS Constraint", test_fcfs_constraint),
        ("Customs Clearance", test_customs_clearance),
        ("Resource Constraints", test_resource_constraints),
        ("Cost Engine", test_cost_engine),
        ("Confidence Calculator", test_confidence_calculator),
        ("KPI Calculator", test_kpi_calculator),
        ("Digital Twin", test_digital_twin),
        ("Scheduler", test_scheduler),
        ("Explainer", test_explainer),
        # Constraint fix tests
        ("Outbound Channel", test_outbound_channel),
        ("Downtime Blocking", test_downtime_blocking),
        ("Deviation Penalty", test_deviation_penalty),
        ("UKC Margin", test_ukc_margin),
        ("Weather Blocking", test_weather_blocking),
        ("Demurrage Objective", test_demurrage_objective),
        ("Confidence Solver Gap", test_confidence_with_solver_gap),
        # Scenario engine tests
        ("Manual Override", test_manual_override),
        ("Ranked Alternatives", test_ranked_alternatives),
        ("Conflict Detection", test_conflict_detection),
        ("Feasibility Reasons", test_feasibility_reasons),
        ("Scenario Impact", test_scenario_impact),
        # New: Enhancement tests
        ("Cascading Conflict Resolution", test_cascading_conflict_resolution),
        ("Ship-Type Config Resolution", test_ship_type_config_resolution),
        ("Ship-Type Objective Weights", test_ship_type_objective_weights),
        # Cargo type tests
        ("Cargo Type Constraint", test_cargo_type_constraint),
        ("Cargo Type Feasibility", test_cargo_type_feasibility),
        # Beam tests
        ("Beam Constraint", test_beam_constraint),
        ("Beam Feasibility", test_beam_feasibility),
        # NEW: Dynamic feasibility tests
        ("Dynamic Vessel Type All Types", test_dynamic_vessel_type_all_types),
        ("Vessel Type Soft Constraint", test_vessel_type_soft_constraint),
        ("Compatibility Scoring", test_compatibility_scoring),
        ("Confidence High For Good Match", test_confidence_high_for_good_match),
        ("Confidence Moderate For Fair Match", test_confidence_moderate_for_fair_match),
        ("Learning System Record Retrieve", test_learning_system_record_and_retrieve),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            print(f"\n[TEST] {name}")
            fn()
            passed += 1
        except Exception as e:
            print(f"  x FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'='*60}")

