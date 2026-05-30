"""
Tests for the Structured Explanation Engine.

Verifies:
  - Physical checks produce correct slack values and status icons
  - Operational assessments detect cargo/vessel type compatibility
  - Performance classification thresholds
  - Infeasible cases show ❌ with correct violations
  - Compact summary is concise and deterministic
  - Final summary uses balanced language (positives + negatives)
  - Comparison insights between berth options
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from engines.analytics.explanation.structured_explanation import (
    StructuredExplanationEngine,
    StructuredExplanation,
    AssessmentStatus,
    ExplanationCategory,
    _classify_numeric_slack,
    build_comparison_insight,
)


@pytest.fixture
def engine():
    return StructuredExplanationEngine()


@pytest.fixture
def sample_vessel():
    return {
        "name": "MV OCEAN STAR",
        "loa": 180.0,
        "draft": 9.5,
        "beam": 28.0,
        "dwt": 30000,
        "vessel_type": "Bulk Carrier",
        "cargo_type": "Coal",
        "cargo_tons": 25000,
    }


@pytest.fixture
def sample_berth():
    return {
        "berth_code": "NCQ1",
        "berth_name": "NCQ1 - North Coal Quay",
        "max_loa_m": 220.0,
        "max_draft_m": 12.0,
        "depth_m": 12.0,
        "max_beam_m": 34.0,
        "allowed_vessel_types": ["Bulk Carrier", "General Cargo"],
        "allowed_cargo_types": ["Coal", "Iron Ore", "Bulk Dry"],
        "equipment": ["crane", "conveyor"],
        "allow_24x7": True,
        "shore_storage_capacity_tons": 50000,
    }


# ── Slack Classification Tests ───────────────────────────────────────────────

class TestSlackClassification:
    def test_strong_fit(self):
        slack, pct, status = _classify_numeric_slack(100, 200)
        assert status == AssessmentStatus.PASS
        assert slack == 100
        assert pct == 0.5

    def test_ok_fit(self):
        slack, pct, status = _classify_numeric_slack(170, 200)
        assert status == AssessmentStatus.OK
        assert slack == 30

    def test_tight_fit(self):
        slack, pct, status = _classify_numeric_slack(194, 200)
        assert status == AssessmentStatus.TIGHT
        assert slack == 6

    def test_violation(self):
        slack, pct, status = _classify_numeric_slack(210, 200)
        assert status == AssessmentStatus.FAIL
        assert slack == -10

    def test_zero_limit(self):
        _, _, status = _classify_numeric_slack(100, 0)
        assert status == AssessmentStatus.UNKNOWN


# ── Physical Fit Tests ────────────────────────────────────────────────────────

class TestPhysicalFit:
    def test_loa_safe_margin(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        loa_item = next(
            (a for a in expl.physical.assessments if a.parameter_name == "LOA"),
            None,
        )
        assert loa_item is not None
        assert loa_item.status in (AssessmentStatus.PASS, AssessmentStatus.OK)
        assert loa_item.slack == 40  # 220 - 180
        assert "180" in loa_item.detail_text
        assert "220" in loa_item.detail_text

    def test_draft_clearance(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        draft_item = next(
            (a for a in expl.physical.assessments if a.parameter_name == "Draft"),
            None,
        )
        assert draft_item is not None
        assert draft_item.status in (AssessmentStatus.PASS, AssessmentStatus.OK)
        assert draft_item.slack == 2.5  # 12.0 - 9.5
        assert "9.5" in draft_item.detail_text

    def test_beam_safe(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        beam_item = next(
            (a for a in expl.physical.assessments if a.parameter_name == "Beam"),
            None,
        )
        assert beam_item is not None
        assert beam_item.status in (AssessmentStatus.PASS, AssessmentStatus.OK)
        assert beam_item.slack == 6  # 34 - 28

    def test_loa_violation(self, engine, sample_berth):
        vessel = {"loa": 250, "draft": 9.5, "beam": 28.0}
        expl = engine.explain(vessel, sample_berth)
        loa_item = next(
            (a for a in expl.physical.assessments if a.parameter_name == "LOA"),
            None,
        )
        assert loa_item is not None
        assert loa_item.status == AssessmentStatus.FAIL
        assert "❌" in loa_item.icon or loa_item.icon == "❌"
        assert not expl.is_feasible

    def test_tight_beam(self, engine, sample_berth):
        vessel = {"loa": 180, "draft": 9.5, "beam": 33.0}
        expl = engine.explain(vessel, sample_berth)
        beam_item = next(
            (a for a in expl.physical.assessments if a.parameter_name == "Beam"),
            None,
        )
        assert beam_item is not None
        assert beam_item.status == AssessmentStatus.TIGHT
        assert "⚠" in beam_item.icon or beam_item.icon == "⚠"


# ── Operational Tests ─────────────────────────────────────────────────────────

class TestOperational:
    def test_cargo_compatible(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        cargo_item = next(
            (a for a in expl.operational.assessments if a.parameter_name == "Cargo Compatibility"),
            None,
        )
        assert cargo_item is not None
        assert cargo_item.status == AssessmentStatus.PASS

    def test_cargo_incompatible(self, engine, sample_berth):
        vessel = {"loa": 180, "draft": 9.5, "cargo_type": "Chemicals"}
        expl = engine.explain(vessel, sample_berth)
        cargo_item = next(
            (a for a in expl.operational.assessments if a.parameter_name == "Cargo Compatibility"),
            None,
        )
        assert cargo_item is not None
        assert cargo_item.status == AssessmentStatus.TIGHT

    def test_vessel_type_supported(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        vt_item = next(
            (a for a in expl.operational.assessments if a.parameter_name == "Vessel Type"),
            None,
        )
        assert vt_item is not None
        assert vt_item.status == AssessmentStatus.PASS

    def test_vessel_type_not_in_list(self, engine, sample_berth):
        vessel = {"loa": 180, "draft": 9.5, "vessel_type": "Tanker"}
        expl = engine.explain(vessel, sample_berth)
        vt_item = next(
            (a for a in expl.operational.assessments if a.parameter_name == "Vessel Type"),
            None,
        )
        assert vt_item is not None
        assert vt_item.status == AssessmentStatus.TIGHT
        # Must NOT say "historically not assigned" — must say "not in allowed types"
        assert "histor" not in vt_item.detail_text.lower()
        assert "not in" in vt_item.detail_text.lower() or "not in allowed" in vt_item.detail_text.lower()

    def test_equipment_shown(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        equip_item = next(
            (a for a in expl.operational.assessments if a.parameter_name == "Equipment"),
            None,
        )
        assert equip_item is not None
        assert equip_item.status == AssessmentStatus.PASS
        assert "crane" in equip_item.detail_text.lower() or "conveyor" in equip_item.detail_text.lower()

    def test_shore_capacity(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth)
        shore_item = next(
            (a for a in expl.operational.assessments if a.parameter_name == "Shore Storage"),
            None,
        )
        assert shore_item is not None
        assert shore_item.status == AssessmentStatus.PASS
        assert "50,000" in shore_item.detail_text or "50000" in shore_item.detail_text


# ── Performance Tests ─────────────────────────────────────────────────────────

class TestPerformance:
    def test_short_wait(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth, wait_hours=1.5, service_hours=14.0)
        wait_item = next(
            (a for a in expl.performance.assessments if a.parameter_name == "Waiting Time"),
            None,
        )
        assert wait_item is not None
        assert wait_item.status == AssessmentStatus.PASS
        assert "1.5" in wait_item.detail_text

    def test_high_wait(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth, wait_hours=22.4, service_hours=14.0)
        wait_item = next(
            (a for a in expl.performance.assessments if a.parameter_name == "Waiting Time"),
            None,
        )
        assert wait_item is not None
        assert wait_item.status == AssessmentStatus.TIGHT
        assert "22.4" in wait_item.detail_text

    def test_service_time_fast(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(sample_vessel, sample_berth, service_hours=8.0)
        svc_item = next(
            (a for a in expl.performance.assessments if a.parameter_name == "Service Time"),
            None,
        )
        assert svc_item is not None
        assert svc_item.status == AssessmentStatus.PASS


# ── Commercial Tests ──────────────────────────────────────────────────────────

class TestCommercial:
    def test_no_sla_risk(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(
            sample_vessel, sample_berth,
            wait_hours=5.0, service_hours=14.0, sla_max_wait_hours=24.0,
        )
        sla_item = next(
            (a for a in expl.commercial.assessments if a.parameter_name == "SLA Risk"),
            None,
        )
        assert sla_item is not None
        assert sla_item.status == AssessmentStatus.PASS

    def test_sla_breach(self, engine, sample_vessel, sample_berth):
        expl = engine.explain(
            sample_vessel, sample_berth,
            wait_hours=30.0, service_hours=14.0, sla_max_wait_hours=24.0,
        )
        sla_item = next(
            (a for a in expl.commercial.assessments if a.parameter_name == "SLA Risk"),
            None,
        )
        assert sla_item is not None
        assert sla_item.status == AssessmentStatus.FAIL


# ── Summary Tests ─────────────────────────────────────────────────────────────

class TestSummaries:
    def test_compact_summary_deterministic(self, engine, sample_vessel, sample_berth):
        """Same inputs must produce same output."""
        e1 = engine.explain(sample_vessel, sample_berth, wait_hours=5.0, service_hours=14.0)
        e2 = engine.explain(sample_vessel, sample_berth, wait_hours=5.0, service_hours=14.0)
        assert e1.compact_summary == e2.compact_summary
        assert e1.final_summary == e2.final_summary

    def test_compact_summary_not_vague(self, engine, sample_vessel, sample_berth):
        """Compact summary must NOT contain vague terms."""
        expl = engine.explain(sample_vessel, sample_berth, wait_hours=5.0, service_hours=14.0)
        assert "low suitability" not in expl.compact_summary.lower()
        assert "historically" not in expl.compact_summary.lower()
        assert "rarely assigned" not in expl.compact_summary.lower()

    def test_final_summary_uses_parameters(self, engine, sample_vessel, sample_berth):
        """Final summary must reference actual parameters, not generic text."""
        expl = engine.explain(sample_vessel, sample_berth, wait_hours=22.4, service_hours=14.0)
        # Should mention physical fit
        assert "physic" in expl.final_summary.lower() or "suitable" in expl.final_summary.lower()

    def test_infeasible_summary(self, engine, sample_berth):
        """Infeasible vessel shows clear violations."""
        vessel = {"loa": 300, "draft": 15.0, "beam": 28.0}
        expl = engine.explain(vessel, sample_berth)
        assert not expl.is_feasible
        assert "not feasible" in expl.final_summary.lower() or "Not feasible" in expl.final_summary
        assert len(expl.hard_violations) > 0

    def test_balanced_explanation(self, engine, sample_vessel, sample_berth):
        """Explanation has both positives and negatives when there are trade-offs."""
        expl = engine.explain(sample_vessel, sample_berth, wait_hours=22.0, service_hours=14.0)
        # Should have both pros and cons
        assert len(expl.get_pros()) > 0
        assert len(expl.get_cons()) > 0

    def test_compact_summary_concise(self, engine, sample_vessel, sample_berth):
        """Compact summary should be reasonably short."""
        expl = engine.explain(sample_vessel, sample_berth, wait_hours=5.0, service_hours=14.0)
        assert len(expl.compact_summary) < 120


# ── Comparison Tests ──────────────────────────────────────────────────────────

class TestComparison:
    def test_comparison_insight(self, engine, sample_vessel, sample_berth):
        berth_b = dict(sample_berth)
        berth_b["berth_code"] = "JD3"
        berth_b["berth_name"] = "JD3 - Jawahar Dock"

        expl_a = engine.explain(sample_vessel, sample_berth, wait_hours=5.0, service_hours=14.0)
        expl_b = engine.explain(sample_vessel, berth_b, wait_hours=10.0, service_hours=20.0)

        cmp = build_comparison_insight(expl_a, expl_b, 5.0, 10.0, 14.0, 20.0)
        assert "JD3" in cmp or "lower wait" in cmp.lower() or "faster" in cmp.lower()


# ── Integration Tests ─────────────────────────────────────────────────────────

class TestIntegration:
    def test_all_categories_populated(self, engine, sample_vessel, sample_berth):
        """All 4 categories should have at least one assessment."""
        expl = engine.explain(
            sample_vessel, sample_berth,
            wait_hours=5.0, service_hours=14.0,
        )
        assert len(expl.physical.assessments) >= 3  # LOA, Draft, Beam
        assert len(expl.operational.assessments) >= 2  # Cargo, vessel type
        assert len(expl.performance.assessments) >= 1  # Wait time
        assert len(expl.commercial.assessments) >= 1  # SLA

    def test_no_generic_text(self, engine, sample_vessel, sample_berth):
        """None of the detail texts should contain generic/vague phrases."""
        expl = engine.explain(
            sample_vessel, sample_berth,
            wait_hours=5.0, service_hours=14.0,
        )
        for a in expl.all_assessments:
            assert "low suitability" not in a.detail_text.lower()
            assert "historically not assigned" not in a.detail_text.lower()
            assert "rarely assigned" not in a.detail_text.lower()

    def test_status_icon_consistency(self, engine, sample_vessel, sample_berth):
        """Each status should have the correct icon."""
        expl = engine.explain(sample_vessel, sample_berth)
        for a in expl.all_assessments:
            if a.status == AssessmentStatus.PASS:
                assert a.icon == "✔"
            elif a.status == AssessmentStatus.FAIL:
                assert a.icon == "❌"
            elif a.status == AssessmentStatus.TIGHT:
                assert a.icon == "⚠"
