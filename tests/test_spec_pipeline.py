"""
Tests for Spec-Based Data Pipeline
===================================
Validates:
  1. BerthSpec model and ProvenanceField
  2. ConstraintLibrary builds constraints from BerthSpec
  3. FeasibilityChecker uses spec limits when PortMaster provided
  4. config.py auto-loads PortMaster from sample_data/
  5. Data quality scoring
  6. Spec ingestion from Excel (if files present)
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

from data_models import (
    BerthSpec, PortMaster, ProvenanceField, DataSource, QualityGate,
    ConstraintDefinition, ConstraintCategory, ConstraintSeverity,
    FeasibilityResult, ConstraintCheckResult,
)
from optimization_engine.constraint_model import VesselInput, BerthInput, SchedulerConfig
from optimization_engine.feasibility_checker import FeasibilityChecker


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_berth_spec(
    bc="B1", max_loa=200, max_draft=12, max_depth=14, max_beam=32,
    ukc=1.0, vessel_types=None, cargo_cats=None,
):
    """Build a BerthSpec with spec-sourced fields."""
    spec = BerthSpec(
        berth_code=bc,
        berth_name=f"Test Berth {bc}",
        terminal_code="T1",
        terminal_name="Test Terminal",
        port_code="P1",
        port_name="Test Port",
    )
    spec.max_loa_m = ProvenanceField.from_spec(float(max_loa), "Test spec")
    spec.max_draft_m = ProvenanceField.from_spec(float(max_draft))
    spec.max_depth_m = ProvenanceField.from_spec(float(max_depth))
    spec.max_beam_m = ProvenanceField.from_spec(float(max_beam))
    spec.ukc_m = ProvenanceField.from_spec(float(ukc))
    if vessel_types:
        spec.allowed_vessel_types = vessel_types
        spec.vessel_type_source = DataSource.OPERATIONAL
    if cargo_cats:
        spec.cargo_categories = set(cargo_cats)
    return spec


def _make_port_master(*berth_specs):
    """Build a PortMaster from BerthSpec objects."""
    berths = {s.berth_code: s for s in berth_specs}
    return PortMaster(
        port_code="TEST",
        port_name="Test Port",
        berths=berths,
        spec_loaded=True,
        operational_loaded=True,
    )


def _make_vessel(vid="V1", loa=180, draft=10, beam=28, vtype="BULK CARRIER", cargo="Dry"):
    return VesselInput(
        vessel_id=vid, name=f"Test {vid}",
        vessel_type=vtype, cargo_type=cargo,
        loa_m=loa, beam_m=beam, draft_m=draft,
        cargo_tons=25000,
        eta_minutes=0, service_time_minutes=720,
        customs_cleared=True,
    )


def _make_berth_input(bc="B1", max_loa=200, max_draft=12, max_beam=32, depth=14):
    return BerthInput(
        berth_code=bc, berth_name=f"Berth {bc}",
        max_loa_m=max_loa, max_draft_m=max_draft,
        max_beam_m=max_beam, depth_m=depth,
        allowed_vessel_types=["BULK CARRIER"],
    )


# ══════════════════════════════════════════════════════════════════════════
#  TEST 1: BerthSpec and ProvenanceField
# ══════════════════════════════════════════════════════════════════════════

def test_provenance_field():
    """ProvenanceField correctly tracks source and quality."""
    pf_spec = ProvenanceField.from_spec(200.0, "From berth config")
    assert pf_spec.source == DataSource.SPEC
    assert pf_spec.quality == QualityGate.GREEN
    assert pf_spec.value == 200.0

    pf_hist = ProvenanceField.from_history(180.0, "From max observed")
    assert pf_hist.source == DataSource.HISTORICAL
    assert pf_hist.quality == QualityGate.YELLOW

    pf_assume = ProvenanceField.from_assumption(0.0, "No data")
    assert pf_assume.source == DataSource.ASSUMPTION
    assert pf_assume.quality == QualityGate.RED


def test_berth_spec_getters():
    """BerthSpec getter methods return correct values."""
    spec = _make_berth_spec(max_loa=250, max_draft=14, max_depth=16, max_beam=40, ukc=1.5)
    assert spec.get_max_loa() == 250.0
    assert spec.get_max_draft() == 14.0
    assert spec.get_depth() == 16.0
    assert spec.get_max_beam() == 40.0
    assert spec.get_ukc() == 1.5


def test_berth_spec_legacy_dict():
    """to_legacy_dict() produces backward-compatible output."""
    spec = _make_berth_spec(max_loa=200, max_draft=12, cargo_cats=["Dry", "Wet"])
    d = spec.to_legacy_dict()
    assert d["berth_code"] == "B1"
    assert d["max_loa_m"] == 200.0
    assert d["max_draft_m"] == 12.0
    assert d["loa_source"] == "spec"
    assert "Dry" in d["cargo_categories"]
    assert "data_quality" in d


# ══════════════════════════════════════════════════════════════════════════
#  TEST 2: ConstraintLibrary
# ══════════════════════════════════════════════════════════════════════════

def test_constraint_library_builds():
    """ConstraintLibrary builds typed constraints from BerthSpec."""
    from optimization_engine.constraint_library import ConstraintLibrary

    spec = _make_berth_spec(
        max_loa=200, max_draft=12, max_depth=14, max_beam=32, ukc=1.0,
        vessel_types=["BULK CARRIER"], cargo_cats=["Dry"],
    )
    pm = _make_port_master(spec)
    lib = ConstraintLibrary(pm)

    constraints = lib.get_constraints("B1")
    assert len(constraints) > 0

    # Check we have LOA, draft, depth/UKC, beam constraints
    ids = [c.id for c in constraints]
    assert "B1_loa" in ids, f"Missing LOA constraint, got: {ids}"
    assert "B1_draft" in ids, f"Missing draft constraint, got: {ids}"
    assert "B1_depth_ukc" in ids, f"Missing depth/UKC constraint, got: {ids}"
    assert "B1_beam" in ids, f"Missing beam constraint, got: {ids}"

    # Check severity
    loa_c = next(c for c in constraints if c.id == "B1_loa")
    assert loa_c.severity == ConstraintSeverity.HARD
    assert loa_c.source == DataSource.SPEC


def test_constraint_library_feasibility_pass():
    """Vessel within all limits passes feasibility."""
    from optimization_engine.constraint_library import ConstraintLibrary

    spec = _make_berth_spec(max_loa=250, max_draft=15, max_depth=18, max_beam=40)
    pm = _make_port_master(spec)
    lib = ConstraintLibrary(pm)

    vessel = {"vessel_id": "V1", "loa": 180, "draft": 10, "beam": 28, "dwt": 30000}
    result = lib.check_feasibility(vessel, "B1")

    assert result.feasible, f"Should be feasible: {result.explanation}"
    assert result.hard_violations == 0


def test_constraint_library_feasibility_fail_loa():
    """Vessel exceeding LOA limit is correctly rejected."""
    from optimization_engine.constraint_library import ConstraintLibrary

    spec = _make_berth_spec(max_loa=150, max_draft=15, max_depth=18, max_beam=40)
    pm = _make_port_master(spec)
    lib = ConstraintLibrary(pm)

    vessel = {"vessel_id": "V1", "loa": 200, "draft": 10, "beam": 28}
    result = lib.check_feasibility(vessel, "B1")

    assert not result.feasible, "Should be infeasible (LOA exceeded)"
    assert result.hard_violations >= 1


def test_constraint_library_feasibility_fail_draft():
    """Vessel exceeding draft limit is correctly rejected."""
    from optimization_engine.constraint_library import ConstraintLibrary

    spec = _make_berth_spec(max_loa=300, max_draft=9.5, max_depth=12, max_beam=40)
    pm = _make_port_master(spec)
    lib = ConstraintLibrary(pm)

    vessel = {"vessel_id": "V1", "loa": 180, "draft": 11, "beam": 28}
    result = lib.check_feasibility(vessel, "B1")

    assert not result.feasible, "Should be infeasible (draft exceeded)"
    assert result.hard_violations >= 1


def test_constraint_library_suitability_score():
    """Suitability score ranks matching berths higher."""
    from optimization_engine.constraint_library import ConstraintLibrary

    spec_bulk = _make_berth_spec(
        bc="B_BULK", max_loa=250, max_draft=15, max_depth=18, max_beam=40,
        vessel_types=["BULK CARRIER"], cargo_cats=["Dry"],
    )
    spec_container = _make_berth_spec(
        bc="B_CONT", max_loa=350, max_draft=15, max_depth=18, max_beam=50,
        vessel_types=["CONTAINER SHIP"], cargo_cats=["Dry"],
    )
    pm = _make_port_master(spec_bulk, spec_container)
    lib = ConstraintLibrary(pm)

    vessel = {"vessel_id": "V1", "loa": 180, "draft": 10, "beam": 28,
              "vessel_type": "BULK CARRIER", "cargo_category": "Dry"}

    score_bulk = lib.compute_suitability_score(vessel, "B_BULK")
    score_cont = lib.compute_suitability_score(vessel, "B_CONT")

    assert score_bulk > score_cont, (
        f"Bulk berth should score higher for bulk carrier: {score_bulk} vs {score_cont}"
    )


# ══════════════════════════════════════════════════════════════════════════
#  TEST 3: FeasibilityChecker with PortMaster (spec-backed)
# ══════════════════════════════════════════════════════════════════════════

def test_checker_uses_spec_loa():
    """FeasibilityChecker uses spec LOA limit instead of BerthInput limit."""
    # BerthInput says max_loa=300 (history-derived with 10% buffer)
    # But spec says max_loa=200 (authoritative)
    berth_input = _make_berth_input(bc="B1", max_loa=300)

    spec = _make_berth_spec(bc="B1", max_loa=200)
    pm = _make_port_master(spec)

    vessel = _make_vessel(loa=250)  # Fits history (300) but not spec (200)

    # Without PortMaster -> passes (uses BerthInput's 300m limit)
    checker_no_spec = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0))
    report_no_spec = checker_no_spec.check(vessel, berth_input)
    assert report_no_spec.feasible, "Should pass without spec (300m limit)"

    # With PortMaster -> fails (uses spec's 200m limit)
    checker_spec = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0), port_master=pm)
    report_spec = checker_spec.check(vessel, berth_input)
    assert not report_spec.feasible, "Should fail with spec (200m limit, vessel 250m)"

    # Verify the check detail mentions the spec source
    loa_check = next(c for c in report_spec.checks if c.name == "LOA fit")
    assert "spec" in loa_check.detail.lower(), f"Detail should mention spec source: {loa_check.detail}"


def test_checker_uses_spec_draft():
    """FeasibilityChecker uses spec draft limit and UKC."""
    berth_input = _make_berth_input(bc="B1", max_draft=15, depth=16)

    spec = _make_berth_spec(bc="B1", max_draft=10, max_depth=12, ukc=1.0)
    pm = _make_port_master(spec)

    vessel = _make_vessel(draft=11)  # Fits history (15) but not spec (10)

    checker_spec = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0), port_master=pm)
    report = checker_spec.check(vessel, berth_input)
    assert not report.feasible, "Draft 11m > spec max_draft 10m"


def test_checker_uses_spec_beam():
    """FeasibilityChecker uses spec beam limit."""
    berth_input = _make_berth_input(bc="B1", max_beam=50)

    spec = _make_berth_spec(bc="B1", max_beam=25)
    pm = _make_port_master(spec)

    vessel = _make_vessel(beam=30)  # Fits history (50) but not spec (25)

    checker_spec = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0), port_master=pm)
    report = checker_spec.check(vessel, berth_input)
    assert not report.feasible, "Beam 30m > spec max_beam 25m"


def test_checker_backward_compat():
    """FeasibilityChecker works without PortMaster (backward compatible)."""
    berth_input = _make_berth_input(bc="B1", max_loa=200, max_draft=12, max_beam=32, depth=14)
    vessel = _make_vessel(loa=180, draft=10, beam=28)

    checker = FeasibilityChecker(SchedulerConfig(ukc_margin_m=0.5))
    report = checker.check(vessel, berth_input)
    assert report.feasible, f"Should pass: {report.violation_summary}"


# ══════════════════════════════════════════════════════════════════════════
#  TEST 4: Data Quality
# ══════════════════════════════════════════════════════════════════════════

def test_quality_scoring():
    """Quality scoring produces expected gates."""
    from data_layer.quality import score_berth_quality

    # Well-specified berth -> GREEN
    spec_good = _make_berth_spec(
        max_loa=200, max_draft=12, max_depth=14, max_beam=32,
        vessel_types=["BULK CARRIER"], cargo_cats=["Dry"],
    )
    eq_good = score_berth_quality(spec_good)
    assert eq_good.overall_gate in (QualityGate.GREEN, QualityGate.YELLOW), (
        f"Well-specified berth should be GREEN/YELLOW, got {eq_good.overall_gate} ({eq_good.overall_score})"
    )

    # Poorly-specified berth -> RED
    spec_bad = BerthSpec(berth_code="B_BAD", berth_name="Bad Berth")
    eq_bad = score_berth_quality(spec_bad)
    assert eq_bad.overall_gate == QualityGate.RED, (
        f"Poorly-specified berth should be RED, got {eq_bad.overall_gate} ({eq_bad.overall_score})"
    )


# ══════════════════════════════════════════════════════════════════════════
#  TEST 5: Spec Ingestion from Excel (conditional)
# ══════════════════════════════════════════════════════════════════════════

def test_spec_ingestion():
    """Spec ingestion reads Excel files and builds PortMaster (skip if files missing)."""
    sample_data = Path(__file__).resolve().parent.parent / "sample_data"
    bcfg = sample_data / "Berth_configurations.xlsx"

    if not bcfg.exists():
        return  # Skip if no spec files

    from legacy.spec_ingest import build_port_master

    pm = build_port_master(
        port_name="test_chennai",
        berth_config_path=str(bcfg),
        operational_capability_path=str(sample_data / "Operational_Capability_of_Berth.xlsx"),
    )

    assert len(pm.berths) > 0, "Should build at least one berth"
    assert pm.spec_loaded is True

    # Verify at least one berth has spec-sourced LOA
    has_spec_loa = any(
        b.max_loa_m.source == DataSource.SPEC
        for b in pm.berths.values()
        if b.get_max_loa() > 0
    )
    assert has_spec_loa, "At least one berth should have spec-sourced LOA"


def test_constraint_library_from_excel():
    """ConstraintLibrary builds from real spec files (skip if files missing)."""
    sample_data = Path(__file__).resolve().parent.parent / "sample_data"
    bcfg = sample_data / "Berth_configurations.xlsx"

    if not bcfg.exists():
        return  # Skip

    from legacy.spec_ingest import build_port_master
    from optimization_engine.constraint_library import ConstraintLibrary

    pm = build_port_master(
        port_name="test",
        berth_config_path=str(bcfg),
        operational_capability_path=str(sample_data / "Operational_Capability_of_Berth.xlsx"),
    )

    lib = ConstraintLibrary(pm)
    summary = lib.summary()

    assert summary["total_berths"] > 0
    assert summary["total_constraints"] > 0
    assert summary["spec_coverage_pct"] > 50, (
        f"Spec coverage should be >50%, got {summary['spec_coverage_pct']}%"
    )


# ══════════════════════════════════════════════════════════════════════════
#  TEST 6: Config.py PortMaster Wiring
# ══════════════════════════════════════════════════════════════════════════

def test_config_load_port_master():
    """config._load_port_master_for_config returns PortMaster when spec files exist."""
    sample_data = Path(__file__).resolve().parent.parent / "sample_data"
    bcfg = sample_data / "Berth_configurations.xlsx"

    if not bcfg.exists():
        return  # Skip

    from config import _load_port_master_for_config

    pm = _load_port_master_for_config(port_name="test")
    assert pm is not None, "_load_port_master_for_config should return PortMaster"
    assert len(pm.berths) > 0


# ══════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    ("ProvenanceField", test_provenance_field),
    ("BerthSpec Getters", test_berth_spec_getters),
    ("BerthSpec Legacy Dict", test_berth_spec_legacy_dict),
    ("ConstraintLibrary Builds", test_constraint_library_builds),
    ("Constraint Feasibility Pass", test_constraint_library_feasibility_pass),
    ("Constraint Feasibility Fail LOA", test_constraint_library_feasibility_fail_loa),
    ("Constraint Feasibility Fail Draft", test_constraint_library_feasibility_fail_draft),
    ("Suitability Score Ranking", test_constraint_library_suitability_score),
    ("Checker Uses Spec LOA", test_checker_uses_spec_loa),
    ("Checker Uses Spec Draft", test_checker_uses_spec_draft),
    ("Checker Uses Spec Beam", test_checker_uses_spec_beam),
    ("Checker Backward Compat", test_checker_backward_compat),
    ("Quality Scoring", test_quality_scoring),
    ("Spec Ingestion (Excel)", test_spec_ingestion),
    ("Constraint Library (Excel)", test_constraint_library_from_excel),
    ("Config PortMaster Wiring", test_config_load_port_master),
]

if __name__ == "__main__":
    import traceback

    passed = 0
    failed = 0
    skipped = 0
    for name, fn in ALL_TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name} -- {e}")
            traceback.print_exc()

    print(f"\nSpec Pipeline Tests: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    sys.exit(1 if failed > 0 else 0)
