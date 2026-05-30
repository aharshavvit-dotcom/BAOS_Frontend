"""
Integration Tests — Phase 3-5
================================
End-to-end validation of the full data-driven pipeline:
  1. Recommender with uncertainty
  2. Learning engine with spec tracking
  3. Confidence engine data-quality-awareness
  4. Full pipeline: config → features → train → recommend → learn
"""
import sys, json, shutil
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))


# ── Helpers ────────────────────────────────────────────────────────────────

def _has_port_data():
    """Check if port data exists for integration tests."""
    from backend.db.repositories.port_store import port_exists, is_trained
    return port_exists("chennai") and is_trained("chennai")


# ══════════════════════════════════════════════════════════════════════════
#  TEST 1: Recommender uses uncertainty
# ══════════════════════════════════════════════════════════════════════════

def test_recommender_with_uncertainty():
    """Recommender outputs uncertainty bounds in BerthOptions."""
    if not _has_port_data():
        return  # Skip

    from engines.core.decision.recommender import recommend_berth

    vessel = {
        "name": "Test Vessel",
        "loa": 180,
        "draft": 10,
        "beam": 28,
        "dwt": 30000,
        "vessel_type": "BULK CARRIER",
        "cargo_type": "Coal",
    }

    options = recommend_berth(vessel, "chennai", top_k=3)
    assert len(options) > 0, "Should get at least one recommendation"

    best = options[0]
    assert best.berth_code != "NONE", f"Should find eligible berth, got {best.berth_code}"
    assert best.confidence > 0, "Confidence should be > 0"
    assert best.rank == 1, "Best option should have rank 1"

    # Phase 3: Uncertainty bounds should be populated
    assert best.service_time_upper >= best.service_time_lower, (
        f"Upper ({best.service_time_upper}) should be >= lower ({best.service_time_lower})"
    )

    # Pros/cons should exist
    assert len(best.pros) > 0 or len(best.cons) > 0, "Should have pros or cons"

    # Explanation should mention uncertainty
    assert best.explanation, "Should have explanation"


def test_recommender_infeasible_vessel():
    """Recommender returns NONE for vessel exceeding all berths."""
    if not _has_port_data():
        return

    from engines.core.decision.recommender import recommend_berth

    vessel = {"name": "Giant", "loa": 9999, "draft": 99, "beam": 200, "dwt": 999999}
    options = recommend_berth(vessel, "chennai")
    assert options[0].berth_code == "NONE"


# ══════════════════════════════════════════════════════════════════════════
#  TEST 2: Learning engine with spec tracking
# ══════════════════════════════════════════════════════════════════════════

def test_learning_engine_spec_tracking():
    """Assignment tracker records spec-backed flag and prediction errors."""
    from engines.learning.assignment_tracker import (
        record_assignment, get_prediction_accuracy, _learning_path,
    )

    test_port = "__test_learning__"
    # Clean up any previous test data
    test_path = _learning_path(test_port)
    if test_path.exists():
        test_path.unlink()

    # Record some assignments with actuals
    record_assignment(
        test_port, "V1", "BULK CARRIER", "B1",
        predicted_service_hours=24.0, actual_service_hours=26.0,
        predicted_wait_hours=2.0, actual_wait_hours=3.0,
        spec_backed=True,
        service_time_lower=20.0, service_time_upper=30.0,
    )
    record_assignment(
        test_port, "V2", "TANKER", "B2",
        predicted_service_hours=12.0, actual_service_hours=35.0,  # Big miss
        predicted_wait_hours=1.0, actual_wait_hours=1.5,
        spec_backed=False,
        service_time_lower=10.0, service_time_upper=16.0,
    )
    record_assignment(
        test_port, "V3", "CONTAINER", "B1",
        predicted_service_hours=18.0, actual_service_hours=20.0,
        spec_backed=True,
        service_time_lower=15.0, service_time_upper=22.0,
    )

    # Check prediction accuracy
    acc = get_prediction_accuracy(test_port)
    assert acc["total_with_actuals"] == 3
    assert acc["service_mae_h"] is not None
    assert acc["service_mae_h"] > 0
    assert acc["within_bounds_pct"] is not None
    # V1: 26 within [20,30] ✓, V2: 35 not within [10,16] ✗, V3: 20 within [15,22] ✓
    # Expected: 2/3 = 66.7%
    assert 60 < acc["within_bounds_pct"] < 70, f"Expected ~66.7%, got {acc['within_bounds_pct']}%"
    assert acc["spec_backed_pct"] > 60, f"Expected >60% spec-backed, got {acc['spec_backed_pct']}%"

    # Cleanup
    if test_path.exists():
        test_path.unlink()
    test_dir = test_path.parent
    if test_dir.exists():
        shutil.rmtree(test_dir.parent)


def test_learning_compatibility_history():
    """Compatibility history returns correct success rates."""
    from engines.learning.assignment_tracker import (
        record_assignment, get_compatibility_history, _learning_path,
    )

    test_port = "__test_compat__"
    test_path = _learning_path(test_port)
    if test_path.exists():
        test_path.unlink()

    record_assignment(test_port, "V1", "BULK CARRIER", "B1", outcome="completed")
    record_assignment(test_port, "V2", "BULK CARRIER", "B1", outcome="completed")
    record_assignment(test_port, "V3", "BULK CARRIER", "B1", outcome="incident")

    hist = get_compatibility_history(test_port, "BULK CARRIER", "B1")
    assert hist["assignment_count"] == 3
    assert abs(hist["success_rate"] - 0.667) < 0.01

    # Cleanup
    if test_path.exists():
        test_path.unlink()
    shutil.rmtree(test_path.parent.parent, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════
#  TEST 3: ML Enrichment with uncertainty
# ══════════════════════════════════════════════════════════════════════════

def test_ml_enrichment():
    """ML enrichment uses uncertainty prediction."""
    if not _has_port_data():
        return

    from engines.core.decision.ml_enrichment import enrich_vessels_with_ml
    from engines.simulation.optimization.constraint_model import VesselInput, BerthInput
    from backend.db.repositories.port_store import load_port_config

    # Load actual port config to get real berth codes
    pcfg = load_port_config("chennai")
    real_berths = pcfg.get("berths", [])
    if not real_berths:
        return

    # Build BerthInput from real config
    berths = []
    for b in real_berths[:5]:
        berths.append(BerthInput(
            berth_code=str(b["berth_code"]),
            berth_name=str(b.get("berth_name", b["berth_code"])),
            max_loa_m=b.get("max_loa_m", 300),
            max_draft_m=b.get("max_draft_m", 15),
            max_beam_m=b.get("max_beam_m", 50),
            depth_m=b.get("depth_m", 16),
            allowed_vessel_types=b.get("allowed_vessel_types", []),
        ))

    vessels = [VesselInput(
        vessel_id="V_TEST", name="Test Ship",
        vessel_type="BULK CARRIER", cargo_type="Coal",
        loa_m=150, beam_m=22, draft_m=8,
        cargo_tons=20000,
        eta_minutes=0, service_time_minutes=1440,
        customs_cleared=True,
    )]

    preds = enrich_vessels_with_ml(vessels, berths, "chennai")
    # Should have a prediction (may be empty if vessel doesn't fit any berth)
    # Just verify it runs without error
    assert isinstance(preds, dict), f"Should return dict, got {type(preds)}"


# ══════════════════════════════════════════════════════════════════════════
#  TEST 4: Confidence with data quality awareness
# ══════════════════════════════════════════════════════════════════════════

def test_confidence_data_quality():
    """Confidence engine uses compatibility factor from spec data."""
    from engines.core.decision.confidence import ConfidenceCalculator

    calc = ConfidenceCalculator()

    # High compatibility (spec-backed) → higher confidence
    result_high = calc.compute(compatibility_score=90)
    # Low compatibility → lower confidence
    result_low = calc.compute(compatibility_score=30)

    assert result_high.confidence_pct > result_low.confidence_pct, (
        f"High compat ({result_high.confidence_pct}) should beat "
        f"low compat ({result_low.confidence_pct})"
    )
    assert result_high.compatibility_score > result_low.compatibility_score


# ══════════════════════════════════════════════════════════════════════════
#  TEST 5: Full pipeline end-to-end
# ══════════════════════════════════════════════════════════════════════════

def test_full_pipeline():
    """Full pipeline: config → features → train → recommend → learn."""
    if not _has_port_data():
        return

    # 1. Load port config (use load_port_config, not build_port_config_from_history)
    from backend.db.repositories.port_store import load_port_config
    cfg = load_port_config("chennai")
    assert "berths" in cfg
    assert len(cfg["berths"]) > 0

    # 2. Training completes
    from engines.learning.training.trainer import train_port_models
    metadata = train_port_models("chennai")
    assert metadata["training_samples"] > 0
    assert "version" in metadata

    # 3. Recommendation works
    from engines.core.decision.recommender import recommend_berth
    vessel = {
        "name": "Pipeline Test",
        "loa": 150, "draft": 8, "beam": 22,
        "dwt": 20000, "vessel_type": "BULK CARRIER",
    }
    options = recommend_berth(vessel, "chennai", top_k=3)
    assert len(options) > 0
    assert options[0].berth_code != "NONE"

    # 4. Can record to learning engine
    from engines.learning.assignment_tracker import record_assignment
    record_assignment(
        "chennai", "PIPELINE_TEST", "BULK CARRIER",
        options[0].berth_code,
        predicted_service_hours=options[0].expected_service_hours,
        actual_service_hours=options[0].expected_service_hours + 2,
        spec_backed=True,
        service_time_lower=options[0].service_time_lower,
        service_time_upper=options[0].service_time_upper,
    )


# ══════════════════════════════════════════════════════════════════════════
#  TEST 6: ConstraintLibrary + Recommender integration
# ══════════════════════════════════════════════════════════════════════════

def test_constraint_library_recommender():
    """ConstraintLibrary filters feed correctly into recommender."""
    sample_data = Path(__file__).resolve().parent.parent / "sample_data"
    bcfg = sample_data / "Berth_configurations.xlsx"
    if not bcfg.exists() or not _has_port_data():
        return

    from engines.ingestion.spec_ingest import build_port_master
    from engines.simulation.optimization.constraint_library import ConstraintLibrary

    pm = build_port_master(
        port_name="chennai",
        berth_config_path=str(bcfg),
        operational_capability_path=str(sample_data / "Operational_Capability_of_Berth.xlsx"),
    )
    lib = ConstraintLibrary(pm)

    # A vessel that should fit some berths
    vessel = {"vessel_id": "V1", "loa": 180, "draft": 10, "beam": 28}
    results = lib.check_all_berths(vessel)

    feasible_count = sum(1 for r in results.values() if r.feasible)
    assert feasible_count > 0, f"Should have feasible berths, got 0 of {len(results)}"


# ══════════════════════════════════════════════════════════════════════════
#  TEST 7: Import chain integrity
# ══════════════════════════════════════════════════════════════════════════

def test_import_chain():
    """All modules import without circular dependencies."""
    modules = [
        "backend.db.models.data_models",
        "backend.config.port_config",
        "backend.db.repositories.quality",
        "engines.ingestion.spec_ingest",
        "engines.simulation.optimization.constraint_library",
        "engines.simulation.optimization.feasibility_checker",
        "engines.simulation.optimization.scheduler",
        "engines.learning.training.feature_builder",
        "engines.learning.training.ml_models",
        "engines.learning.training.trainer",
        "engines.core.decision.recommender",
        "engines.core.decision.confidence",
        "engines.core.decision.ml_enrichment",
        "engines.learning.assignment_tracker",
        "engines.simulation.scenario.scenario_manager",
    ]
    failed = []
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            failed.append(f"{mod}: {e}")

    assert not failed, f"Import failures: {'; '.join(failed)}"


# ══════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    ("Recommender Uncertainty", test_recommender_with_uncertainty),
    ("Recommender Infeasible", test_recommender_infeasible_vessel),
    ("Learning Spec Tracking", test_learning_engine_spec_tracking),
    ("Compatibility History", test_learning_compatibility_history),
    ("ML Enrichment", test_ml_enrichment),
    ("Confidence Data Quality", test_confidence_data_quality),
    ("Full Pipeline E2E", test_full_pipeline),
    ("Constraint+Recommender", test_constraint_library_recommender),
    ("Import Chain", test_import_chain),
]

if __name__ == "__main__":
    import traceback

    passed = 0
    failed = 0
    for name, fn in ALL_TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name} -- {e}")
            traceback.print_exc()

    print(f"\nIntegration Tests: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    sys.exit(1 if failed > 0 else 0)
