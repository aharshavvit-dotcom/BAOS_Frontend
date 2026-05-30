"""
Commercial Scorer — Core Integration Engine
Combines technical, commercial, and strategic scores to produce
a final berth recommendation score.

Four decision modes:
  TECHNICAL_ONLY      — weights: tech 50%, constraints 50%
  BALANCED            — weights: tech 35%, commercial 25%, strategic 20%, constraints 20%
  REVENUE_FIRST       — weights: tech 30%, commercial 50%, strategic 0%, constraints 20%
  PARTNERSHIP_FOCUSED — weights: tech 25%, commercial 15%, strategic 40%, constraints 20%
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from engines.analytics.commercial.berth_economics import BerthEconomicsCalculator, RevenueEstimate
from engines.analytics.commercial.partnership_manager import (
    PartnershipManager, VesselCompany, PartnershipTier,
)
from engines.analytics.commercial.dynamic_pricing import DynamicPricingEngine, PricingAdjustment


# ── Decision Mode Weights ─────────────────────────────────────────────────

DECISION_WEIGHTS = {
    "technical_only": {
        "technical": 0.50, "commercial": 0.00, "strategic": 0.00, "constraints": 0.50
    },
    "balanced": {
        "technical": 0.35, "commercial": 0.25, "strategic": 0.20, "constraints": 0.20
    },
    "revenue_first": {
        "technical": 0.30, "commercial": 0.50, "strategic": 0.00, "constraints": 0.20
    },
    "partnership_focused": {
        "technical": 0.25, "commercial": 0.15, "strategic": 0.40, "constraints": 0.20
    },
}


@dataclass
class CommercialDecisionConfig:
    commercial_flag: bool = False
    partnership_system_enabled: bool = True
    dynamic_pricing_enabled: bool = True
    decision_mode: str = "balanced"     # technical_only / balanced / revenue_first / partnership_focused

    @property
    def weights(self) -> dict:
        if not self.commercial_flag:
            return DECISION_WEIGHTS["technical_only"]
        mode = self.decision_mode if self.decision_mode in DECISION_WEIGHTS else "balanced"
        w = dict(DECISION_WEIGHTS[mode])
        if not self.partnership_system_enabled:
            # Redistribute strategic weight to commercial
            w["commercial"] += w["strategic"]
            w["strategic"] = 0.0
        return w


@dataclass
class BerthCommercialResult:
    berth_code: str
    berth_name: str = ""
    # Component scores (0-100)
    technical_score: float = 0.0
    commercial_score: float = 0.0
    strategic_score: float = 0.0
    constraint_score: float = 100.0
    # Final weighted score
    final_score: float = 0.0
    # Revenue details
    revenue_estimate: Optional[RevenueEstimate] = None
    pricing_adjustment: Optional[PricingAdjustment] = None
    # Partnership details
    company: Optional[VesselCompany] = None
    discount_applied_pct: float = 0.0
    sla_compliant: bool = True
    # Metadata
    decision_mode: str = "balanced"
    weights_used: dict = field(default_factory=dict)
    # Human-readable reasoning
    commercial_headline: str = ""
    commercial_reasons: List[str] = field(default_factory=list)
    pricing_note: str = ""


class CommercialScorer:
    """
    Integrates technical, commercial, and strategic scores.

    Usage:
        scorer = CommercialScorer()
        cfg = CommercialDecisionConfig(commercial_flag=True, decision_mode="balanced")

        results = scorer.score_berths(
            vessel_type="Container",
            vessel_company_name="MAERSK",
            berth_options=[{"berth_code": "CTB3", "technical_score": 95, "constraint_score": 100}],
            cargo_quantity=200,
            service_hours=36,
            config=cfg,
        )
        # Returns sorted list of BerthCommercialResult
    """

    def __init__(
        self,
        economics_calc: Optional[BerthEconomicsCalculator] = None,
        partnership_mgr: Optional[PartnershipManager] = None,
        pricing_engine: Optional[DynamicPricingEngine] = None,
    ):
        self._economics = economics_calc or BerthEconomicsCalculator()
        self._partnerships = partnership_mgr or PartnershipManager()
        self._pricing = pricing_engine or DynamicPricingEngine()

    def score_berths(
        self,
        vessel_type: str,
        berth_options: List[dict],
        vessel_company_name: str = "",
        cargo_quantity: float = 0.0,
        cargo_size: str = "20ft",
        service_hours: float = 24.0,
        current_utilization_map: Optional[Dict[str, float]] = None,
        arrival_dt: Optional[datetime] = None,
        is_hazmat: bool = False,
        config: Optional[CommercialDecisionConfig] = None,
    ) -> List[BerthCommercialResult]:
        """
        Score all berth options commercially and return sorted list (best first).

        Args:
            vessel_type: e.g. "Container", "Tanker", "Bulk Carrier"
            berth_options: List of dicts with keys:
                berth_code, berth_name (optional),
                technical_score (0-100), constraint_score (0-100)
            vessel_company_name: e.g. "MAERSK", "SHELL", "" for unknown
            cargo_quantity: Number of containers, tons, or vehicles
            cargo_size: "20ft" / "40ft" / "reefer" / "small" / "medium" / "large"
            service_hours: Expected service duration
            current_utilization_map: {berth_code: utilization 0-1}
            arrival_dt: Expected arrival datetime
            is_hazmat: Whether vessel carries hazardous material
            config: CommercialDecisionConfig (defaults to technical_only if None)

        Returns:
            List of BerthCommercialResult sorted by final_score descending
        """
        cfg = config or CommercialDecisionConfig(commercial_flag=False)
        weights = cfg.weights
        utilization_map = current_utilization_map or {}

        # Lookup partnership data
        company = self._partnerships.lookup(vessel_company_name)
        discount_pct = company.discount_percentage if cfg.commercial_flag and cfg.partnership_system_enabled else 0.0

        results: List[BerthCommercialResult] = []
        max_rev = 0.0  # Track max revenue across options for normalization

        # First pass: compute revenue estimates
        revenue_estimates: Dict[str, RevenueEstimate] = {}
        pricing_adjustments: Dict[str, PricingAdjustment] = {}

        for opt in berth_options:
            bc = opt.get("berth_code", "")
            eco = self._economics.get_berth_economics(bc)
            util = utilization_map.get(bc, 0.75)

            # Dynamic pricing
            if cfg.commercial_flag and cfg.dynamic_pricing_enabled:
                pricing = self._pricing.compute(
                    berth_code=bc,
                    specialization=eco.specialization,
                    current_utilization=util,
                    arrival_dt=arrival_dt,
                    is_hazmat=is_hazmat,
                )
            else:
                pricing = PricingAdjustment(final_multiplier=1.0)

            pricing_adjustments[bc] = pricing

            rev = self._economics.estimate_revenue(
                vessel_type=vessel_type,
                berth_code=bc,
                cargo_quantity=cargo_quantity,
                cargo_size=cargo_size,
                service_hours=service_hours,
                current_utilization=util,
                partnership_discount_pct=discount_pct,
                dynamic_multiplier=pricing.final_multiplier,
            )
            revenue_estimates[bc] = rev
            max_rev = max(max_rev, rev.net_revenue)

        # Second pass: compute scores
        for opt in berth_options:
            bc = opt.get("berth_code", "")
            eco = self._economics.get_berth_economics(bc)
            util = utilization_map.get(bc, 0.75)
            rev = revenue_estimates[bc]
            pricing = pricing_adjustments[bc]

            # ── Technical score (from existing engine) ────────────────────
            tech_score = float(opt.get("technical_score", 50.0))
            constraint_score = float(opt.get("constraint_score", 100.0))

            # ── Commercial score ──────────────────────────────────────────
            if cfg.commercial_flag:
                commercial_score = self._economics.commercial_score_for_berth(
                    vessel_type=vessel_type,
                    berth_code=bc,
                    cargo_quantity=cargo_quantity,
                    cargo_size=cargo_size,
                    service_hours=service_hours,
                    current_utilization=util,
                    partnership_discount_pct=discount_pct,
                    dynamic_multiplier=pricing.final_multiplier,
                    max_expected_revenue=max(max_rev, 1.0),
                )
            else:
                commercial_score = 0.0

            # ── Strategic score ───────────────────────────────────────────
            if cfg.commercial_flag and cfg.partnership_system_enabled:
                is_guaranteed = (
                    company.contract_obligations is not None
                    and bc in company.contract_obligations.guaranteed_berth_types
                )
                strategic_score = self._partnerships.get_strategic_score(
                    company_name=vessel_company_name,
                    berth_code=bc,
                    is_guaranteed_berth=is_guaranteed,
                )
            else:
                strategic_score = 0.0

            # ── Final weighted score ──────────────────────────────────────
            final_score = (
                weights["technical"] * tech_score
                + weights["commercial"] * commercial_score
                + weights["strategic"] * strategic_score
                + weights["constraints"] * constraint_score
            )

            # ── SLA compliance ─────────────────────────────────────────────
            sla_check = self._partnerships.check_sla_obligation(
                vessel_company_name, service_hours
            )
            sla_compliant = sla_check.get("compliant", True)

            # ── Human-readable reasons ────────────────────────────────────
            reasons = []
            tier_badge = company.tier_badge

            if cfg.commercial_flag and cfg.partnership_system_enabled:
                reasons.append(f"Partnership: {tier_badge}")
                if discount_pct > 0:
                    reasons.append(f"Discount applied: {discount_pct:.0f}%")

            if cfg.commercial_flag:
                reasons.append(
                    f"Est. revenue: ${rev.net_revenue:,.0f} "
                    f"({rev.revenue_tier} tier, margin {rev.profit_margin*100:.0f}%)"
                )
                if pricing.final_multiplier != 1.0:
                    reasons.append(f"Dynamic pricing: {pricing.adjustment_reason}")

            headline = (
                f"{tier_badge} | Revenue ${rev.net_revenue:,.0f} | "
                f"Score {final_score:.1f}"
                if cfg.commercial_flag
                else f"Technical score: {tech_score:.0f}"
            )

            result = BerthCommercialResult(
                berth_code=bc,
                berth_name=opt.get("berth_name", bc),
                technical_score=round(tech_score, 2),
                commercial_score=round(commercial_score, 2),
                strategic_score=round(strategic_score, 2),
                constraint_score=round(constraint_score, 2),
                final_score=round(final_score, 2),
                revenue_estimate=rev,
                pricing_adjustment=pricing,
                company=company,
                discount_applied_pct=discount_pct,
                sla_compliant=sla_compliant,
                decision_mode=cfg.decision_mode,
                weights_used=weights,
                commercial_headline=headline,
                commercial_reasons=reasons,
                pricing_note=pricing.adjustment_reason,
            )
            results.append(result)

        # Sort by final_score descending
        results.sort(key=lambda r: r.final_score, reverse=True)
        return results

    def score_single(
        self,
        vessel_type: str,
        berth_code: str,
        berth_name: str = "",
        vessel_company_name: str = "",
        technical_score: float = 75.0,
        constraint_score: float = 100.0,
        cargo_quantity: float = 0.0,
        cargo_size: str = "20ft",
        service_hours: float = 24.0,
        current_utilization: float = 0.75,
        arrival_dt: Optional[datetime] = None,
        is_hazmat: bool = False,
        config: Optional[CommercialDecisionConfig] = None,
    ) -> BerthCommercialResult:
        """Score a single berth option."""
        results = self.score_berths(
            vessel_type=vessel_type,
            berth_options=[{
                "berth_code": berth_code,
                "berth_name": berth_name,
                "technical_score": technical_score,
                "constraint_score": constraint_score,
            }],
            vessel_company_name=vessel_company_name,
            cargo_quantity=cargo_quantity,
            cargo_size=cargo_size,
            service_hours=service_hours,
            current_utilization_map={berth_code: current_utilization},
            arrival_dt=arrival_dt,
            is_hazmat=is_hazmat,
            config=config,
        )
        return results[0] if results else BerthCommercialResult(berth_code=berth_code)
