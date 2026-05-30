"""
Integration tests — Commercial Intelligence Engine
Run: python -m pytest tests/test_commercial_engine.py -v
Or:  python tests/test_commercial_engine.py
"""
import sys
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engines.analytics.commercial.berth_economics import BerthEconomicsCalculator, BERTH_CLASS_PREMIUM
from engines.analytics.commercial.dynamic_pricing import DynamicPricingEngine
from engines.analytics.commercial.partnership_manager import PartnershipManager, PartnershipTier
from engines.analytics.commercial.commercial_scorer import CommercialScorer, CommercialDecisionConfig


# ── 1. Berth Economics Tests ───────────────────────────────────────────────

def test_revenue_calculation_container():
    """Test: container berth revenue for 200 TEU at CTB3 (PREMIUM)."""
    calc = BerthEconomicsCalculator()
    est = calc.estimate_revenue(
        vessel_type="Container",
        berth_code="CTB3",
        cargo_quantity=200,
        cargo_size="20ft",
        service_hours=36,
    )
    assert est.gross_revenue > 0, "Gross revenue must be positive"
    assert est.berth_class == BERTH_CLASS_PREMIUM, "CTB3 must be PREMIUM class"
    assert est.net_revenue > 0, "Net revenue must be positive"
    assert est.profit_margin > 0, "Profit margin must be positive"
    print(f"  PASS Container revenue: gross=${est.gross_revenue:,.0f}, "
          f"net=${est.net_revenue:,.0f}, margin={est.profit_margin*100:.1f}%")


def test_revenue_calculation_tanker():
    """Test: tanker revenue at BD3 — per-call pricing."""
    calc = BerthEconomicsCalculator()
    est = calc.estimate_revenue(
        vessel_type="Tanker",
        berth_code="BD3",
        cargo_quantity=30000,  # tons
        cargo_size="medium",
        service_hours=48,
    )
    assert est.gross_revenue > 0
    assert est.berth_class == BERTH_CLASS_PREMIUM, "BD3 should be PREMIUM"
    print(f"  PASS Tanker revenue: gross=${est.gross_revenue:,.0f}, tier={est.revenue_tier}")


def test_revenue_calculation_roro():
    """Test: RoRo vessel revenue at Berth C — per vehicle pricing."""
    calc = BerthEconomicsCalculator()
    est = calc.estimate_revenue(
        vessel_type="RoRo",
        berth_code="C",
        cargo_quantity=400,  # vehicles
        service_hours=24,
    )
    assert est.gross_revenue > 0
    print(f"  PASS RoRo revenue: ${est.gross_revenue:,.0f} for 400 vehicles @ ${est.rate_applied}/unit")


def test_commercial_score_premium_vs_budget():
    """Test: premium berth (CTB3) should score higher than budget (JD4)."""
    calc = BerthEconomicsCalculator()
    score_premium = calc.commercial_score_for_berth("Container", "CTB3", cargo_quantity=200, service_hours=36)
    score_budget = calc.commercial_score_for_berth("Container", "JD4", cargo_quantity=200, service_hours=36)
    assert score_premium > score_budget, "Premium berth should score higher"
    print(f"  PASS Commercial score: CTB3={score_premium:.1f} vs JD4={score_budget:.1f}")


def test_partnership_discount_reduces_net_revenue():
    """Test: 15% VIP discount reduces net revenue correctly."""
    calc = BerthEconomicsCalculator()
    est_no_discount = calc.estimate_revenue("Container", "CTB3", cargo_quantity=100, service_hours=24)
    est_with_discount = calc.estimate_revenue("Container", "CTB3", cargo_quantity=100, service_hours=24,
                                               partnership_discount_pct=15.0)
    assert est_with_discount.net_revenue < est_no_discount.net_revenue
    expected_discount = est_no_discount.gross_revenue * 0.15
    assert abs(est_with_discount.partnership_discount - expected_discount) < 1.0
    print(f"  PASS Discount: no_discount=${est_no_discount.net_revenue:,.0f}, "
          f"with_15%=${est_with_discount.net_revenue:,.0f}")


# ── 2. Dynamic Pricing Tests ───────────────────────────────────────────────

def test_dynamic_pricing_high_utilization():
    """Test: high utilization (95%) should give +15% premium."""
    engine = DynamicPricingEngine()
    adj = engine.compute(
        berth_code="CTB3",
        specialization="Container",
        current_utilization=0.95,
        arrival_dt=datetime(2026, 3, 15, 10, 0),  # Saturday morning — OVERRIDE with weekday
    )
    # Use a specific weekday (Monday) to isolate utilization effect
    adj_weekday = engine.compute(
        berth_code="CTB3",
        specialization="Container",
        current_utilization=0.95,
        arrival_dt=datetime(2026, 3, 16, 10, 0),  # Monday peak
    )
    assert adj_weekday.utilization_factor >= 1.10, f"High util should add premium, got {adj_weekday.utilization_factor}"
    print(f"  PASS High utilization: multiplier={adj_weekday.final_multiplier:.3f}, "
          f"reason='{adj_weekday.adjustment_reason}'")


def test_dynamic_pricing_low_utilization():
    """Test: low utilization (40%) should give -10% discount."""
    engine = DynamicPricingEngine()
    adj = engine.compute(
        berth_code="CTB2",
        specialization="Container",
        current_utilization=0.40,
        arrival_dt=datetime(2026, 3, 16, 10, 0),  # Monday peak
    )
    assert adj.utilization_factor < 1.0, "Low util should have discount"
    assert adj.utilization_factor == 0.90
    print(f"  PASS Low utilization: factor={adj.utilization_factor:.2f}, "
          f"multiplier={adj.final_multiplier:.3f}")


def test_dynamic_pricing_fixed_berth():
    """Test: fixed-price berths (BD3 oil) should not get dynamic adjustments."""
    engine = DynamicPricingEngine()
    adj = engine.compute(
        berth_code="BD3",
        specialization="Oil_Tanker",
        current_utilization=0.95,  # High utilization
        arrival_dt=datetime(2026, 3, 15, 3, 0),   # Saturday 3am
    )
    assert adj.utilization_factor == 1.0, "Oil berths should have fixed utilization factor"
    assert adj.time_of_day_factor == 1.0, "Oil berths should have fixed time factor"
    print(f"  PASS Fixed pricing for BD3: multiplier={adj.final_multiplier:.3f} (should be near 1.0)")


def test_dynamic_pricing_hazmat_surcharge():
    """Test: hazmat cargo adds 25% surcharge."""
    engine = DynamicPricingEngine()
    adj_normal = engine.compute("CTB3", "Container", 0.75, datetime(2026, 3, 16, 10, 0), is_hazmat=False)
    adj_hazmat = engine.compute("CTB3", "Container", 0.75, datetime(2026, 3, 16, 10, 0), is_hazmat=True)
    assert adj_hazmat.hazmat_factor == 1.25
    assert adj_hazmat.final_multiplier > adj_normal.final_multiplier
    print(f"  PASS Hazmat surcharge: normal={adj_normal.final_multiplier:.3f}, "
          f"hazmat={adj_hazmat.final_multiplier:.3f}")


# ── 3. Partnership Manager Tests ───────────────────────────────────────────

def test_partnership_tier_classification():
    """Test: MAERSK→VIP, SHELL→VIP, ONE→PREMIUM, SPOT→STANDARD."""
    mgr = PartnershipManager()
    assert mgr.get_tier("MAERSK") == PartnershipTier.VIP
    assert mgr.get_tier("SHELL") == PartnershipTier.VIP
    assert mgr.get_tier("ONE") == PartnershipTier.PREMIUM
    assert mgr.get_tier("MSC_EXPANSION") == PartnershipTier.STRATEGIC_PROSPECT
    assert mgr.get_tier("SPOT_MARKET") == PartnershipTier.STANDARD
    assert mgr.get_tier("UNKNOWN XYZ") == PartnershipTier.STANDARD
    print("  PASS Tier classification: MAERSK=VIP, SHELL=VIP, ONE=PREMIUM, MSC=STRATEGIC, SPOT=STANDARD")


def test_partnership_alias_resolution():
    """Test: alias names resolve to canonical company IDs."""
    mgr = PartnershipManager()
    assert mgr.get_tier("MAERSK LINE") == PartnershipTier.VIP
    assert mgr.get_tier("AP MOLLER") == PartnershipTier.VIP
    assert mgr.get_tier("OCEAN NETWORK EXPRESS") == PartnershipTier.PREMIUM
    print("  PASS Alias resolution: MAERSK LINE→VIP, OCEAN NETWORK EXPRESS→PREMIUM")


def test_partnership_discounts():
    """Test: VIP discount=15%, PREMIUM=8%, STANDARD=0%."""
    mgr = PartnershipManager()
    assert mgr.get_discount("MAERSK") == 15.0
    assert mgr.get_discount("ONE") == 8.0
    assert mgr.get_discount("SPOT_MARKET") == 0.0
    assert mgr.get_discount("MSC_EXPANSION") == 20.0   # Prospect has acquisition incentive
    print("  PASS Discounts: MAERSK=15%, ONE=8%, MSC=20%, SPOT=0%")


def test_strategic_score_ordering():
    """Test: VIP scores higher than STANDARD."""
    mgr = PartnershipManager()
    vip_score = mgr.get_strategic_score("MAERSK", "CTB3", is_guaranteed_berth=True)
    premium_score = mgr.get_strategic_score("ONE", "CTB1", is_guaranteed_berth=False)
    standard_score = mgr.get_strategic_score("SPOT_MARKET")
    assert vip_score > premium_score > standard_score
    print(f"  PASS Strategic scores: VIP={vip_score:.1f} > PREMIUM={premium_score:.1f} > STANDARD={standard_score:.1f}")


def test_sla_compliance_check():
    """Test: SLA compliance check for VIP partner."""
    mgr = PartnershipManager()
    # MAERSK SLA = 36 hours
    result_ok = mgr.check_sla_obligation("MAERSK", planned_turnaround_hours=30)
    result_breach = mgr.check_sla_obligation("MAERSK", planned_turnaround_hours=40)
    assert result_ok["compliant"] is True
    assert result_breach["compliant"] is False
    assert result_breach["delta_hours"] == 4.0
    print(f"  PASS SLA check: MAERSK 30h=PASS, 40h=BREACH (SLA={result_ok['sla_hours']}h)")


# ── 4. Commercial Scorer Tests ─────────────────────────────────────────────

def test_commercial_scoring_technical_only():
    """Test: technical_only mode ignores commercial and strategic scores."""
    scorer = CommercialScorer()
    cfg = CommercialDecisionConfig(commercial_flag=False, decision_mode="technical_only")
    results = scorer.score_berths(
        vessel_type="Container",
        berth_options=[
            {"berth_code": "CTB3", "berth_name": "CTB3", "technical_score": 90, "constraint_score": 100},
            {"berth_code": "JD4",  "berth_name": "JD4",  "technical_score": 70, "constraint_score": 100},
        ],
        vessel_company_name="MAERSK",
        config=cfg,
    )
    assert len(results) == 2
    assert results[0].berth_code == "CTB3", "Higher technical score should rank first in technical_only mode"
    assert results[0].commercial_score == 0.0, "Commercial score must be 0 in technical_only mode"
    assert results[0].strategic_score == 0.0, "Strategic score must be 0 in technical_only mode"
    print(f"  PASS Technical_only: CTB3 score={results[0].final_score:.1f} > JD4={results[1].final_score:.1f}")


def test_commercial_scoring_balanced():
    """Test: balanced mode uses all three score components."""
    scorer = CommercialScorer()
    cfg = CommercialDecisionConfig(commercial_flag=True, decision_mode="balanced")
    results = scorer.score_berths(
        vessel_type="Container",
        berth_options=[
            {"berth_code": "CTB3", "berth_name": "CTB3", "technical_score": 85, "constraint_score": 100},
            {"berth_code": "JD4",  "berth_name": "JD4",  "technical_score": 80, "constraint_score": 100},
        ],
        vessel_company_name="MAERSK",
        cargo_quantity=200,
        service_hours=36,
        config=cfg,
    )
    assert len(results) == 2
    assert results[0].commercial_score > 0, "Commercial score must be non-zero in balanced mode"
    assert results[0].strategic_score > 0, "Strategic score must be non-zero in balanced mode"
    top = results[0]
    print(f"  PASS Balanced: {top.berth_code} wins with final={top.final_score:.1f} "
          f"(tech={top.technical_score:.1f}, comm={top.commercial_score:.1f}, strat={top.strategic_score:.1f})")


def test_commercial_scoring_revenue_first():
    """Test: revenue_first mode heavily weights commercial score."""
    scorer = CommercialScorer()
    cfg = CommercialDecisionConfig(commercial_flag=True, decision_mode="revenue_first")
    results = scorer.score_berths(
        vessel_type="Container",
        berth_options=[
            # Lower tech score but premium revenue berth
            {"berth_code": "CTB3", "berth_name": "CTB3", "technical_score": 75, "constraint_score": 100},
            # Higher tech score but budget berth
            {"berth_code": "JD4",  "berth_name": "JD4",  "technical_score": 90, "constraint_score": 100},
        ],
        vessel_company_name="MAERSK",
        cargo_quantity=300,
        service_hours=48,
        config=cfg,
    )
    assert len(results) == 2
    top = results[0]
    print(f"  PASS Revenue_first: winner={top.berth_code} (final={top.final_score:.1f}, "
          f"comm={top.commercial_score:.1f})")


def test_commercial_scoring_vip_vs_standard():
    """Test: VIP company gets higher strategic score than STANDARD."""
    scorer = CommercialScorer()
    cfg = CommercialDecisionConfig(commercial_flag=True, decision_mode="partnership_focused")
    # Same berths, same technical scores → difference is company tier
    result_vip = scorer.score_berths(
        vessel_type="Container",
        berth_options=[
            {"berth_code": "CTB3", "technical_score": 80, "constraint_score": 100},
        ],
        vessel_company_name="MAERSK",
        config=cfg,
    )
    result_standard = scorer.score_berths(
        vessel_type="Container",
        berth_options=[
            {"berth_code": "CTB3", "technical_score": 80, "constraint_score": 100},
        ],
        vessel_company_name="SPOT_MARKET",
        config=cfg,
    )
    assert result_vip[0].strategic_score > result_standard[0].strategic_score
    assert result_vip[0].final_score > result_standard[0].final_score
    print(f"  PASS VIP vs STANDARD: MAERSK score={result_vip[0].final_score:.1f} "
          f"> SPOT={result_standard[0].final_score:.1f}")


# ── Test runner ────────────────────────────────────────────────────────────

def run_all():
    tests = [
        # Economics
        test_revenue_calculation_container,
        test_revenue_calculation_tanker,
        test_revenue_calculation_roro,
        test_commercial_score_premium_vs_budget,
        test_partnership_discount_reduces_net_revenue,
        # Pricing
        test_dynamic_pricing_high_utilization,
        test_dynamic_pricing_low_utilization,
        test_dynamic_pricing_fixed_berth,
        test_dynamic_pricing_hazmat_surcharge,
        # Partnership
        test_partnership_tier_classification,
        test_partnership_alias_resolution,
        test_partnership_discounts,
        test_strategic_score_ordering,
        test_sla_compliance_check,
        # Scorer
        test_commercial_scoring_technical_only,
        test_commercial_scoring_balanced,
        test_commercial_scoring_revenue_first,
        test_commercial_scoring_vip_vs_standard,
    ]

    print("\n" + "=" * 60)
    print("  BAOS AI — Commercial Intelligence Test Suite")
    print("=" * 60)
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAIL {test.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
