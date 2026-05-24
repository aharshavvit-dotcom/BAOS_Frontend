"""Minimal test runner with ASCII output."""
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_optimizer import (
    test_basic_assignment, test_multi_vessel_no_overlap,
    test_infeasible_vessel, test_feasibility_checker,
    test_fcfs_constraint, test_customs_clearance,
    test_resource_constraints, test_cost_engine,
    test_confidence_calculator, test_kpi_calculator,
    test_digital_twin, test_scheduler, test_explainer,
    test_outbound_channel, test_downtime_blocking,
    test_deviation_penalty, test_ukc_margin,
    test_weather_blocking, test_demurrage_objective,
    test_confidence_with_solver_gap,
    test_manual_override, test_ranked_alternatives,
    test_conflict_detection, test_feasibility_reasons,
    test_scenario_impact,
)

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
]

passed = 0
failed = 0
for name, fn in tests:
    try:
        fn()
        passed += 1
        print(f"PASS: {name}")
    except Exception as e:
        failed += 1
        print(f"FAIL: {name} -- {e}")
        traceback.print_exc()

print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)}")
sys.exit(1 if failed > 0 else 0)
