"""
Berth Economics Calculator
Computes revenue, cost, and profit for berth assignments per vessel type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


# ── Berth Classification ───────────────────────────────────────────────────

BERTH_CLASS_PREMIUM = "PREMIUM"
BERTH_CLASS_STANDARD = "STANDARD"
BERTH_CLASS_BUDGET = "BUDGET"


@dataclass
class BerthEconomics:
    berth_code: str
    berth_class: str = BERTH_CLASS_STANDARD
    specialization: str = "GENERAL"           # Container, Oil_Tanker, RoRo, Multipurpose, Chemical
    base_operating_cost_per_hour: float = 900.0
    # Revenue rates by type
    rate_per_20ft_container: float = 600.0
    rate_per_40ft_container: float = 800.0
    rate_per_reefer_container: float = 1200.0
    rate_per_ton_bulk: float = 25.0
    rate_per_ton_general: float = 30.0
    rate_per_ton_oil_small: float = 2500.0    # flat per call for small tanker
    rate_per_ton_oil_medium: float = 4500.0
    rate_per_ton_oil_large: float = 7000.0
    rate_per_vehicle: float = 75.0
    rate_per_call_chemical: float = 3500.0
    # Economics
    monthly_fixed_cost: float = 30000.0
    avg_revenue_per_call: float = 60000.0
    estimated_profit_margin: float = 0.45
    utilization_target_low: float = 0.70
    utilization_target_high: float = 0.85
    # Dynamic pricing thresholds
    dp_high_utilization: float = 0.90
    dp_low_utilization: float = 0.50
    dp_high_premium: float = 0.15
    dp_low_discount: float = 0.10


# ── Default berth economics database (fallback if DB unavailable) ──────────

DEFAULT_BERTH_ECONOMICS: Dict[str, BerthEconomics] = {
    "CTB3": BerthEconomics(
        berth_code="CTB3", berth_class=BERTH_CLASS_PREMIUM, specialization="Container",
        base_operating_cost_per_hour=1500, rate_per_20ft_container=600,
        rate_per_40ft_container=800, rate_per_reefer_container=1200,
        monthly_fixed_cost=50000, avg_revenue_per_call=120000,
        estimated_profit_margin=0.55, utilization_target_low=0.80,
        utilization_target_high=0.90, dp_high_premium=0.15, dp_low_discount=0.10,
    ),
    "CTB2": BerthEconomics(
        berth_code="CTB2", berth_class=BERTH_CLASS_STANDARD, specialization="Container",
        base_operating_cost_per_hour=1200, rate_per_20ft_container=580,
        rate_per_40ft_container=760, rate_per_reefer_container=1100,
        monthly_fixed_cost=40000, avg_revenue_per_call=100000,
        estimated_profit_margin=0.50,
    ),
    "CTB1": BerthEconomics(
        berth_code="CTB1", berth_class=BERTH_CLASS_STANDARD, specialization="Container",
        base_operating_cost_per_hour=1200, rate_per_20ft_container=560,
        rate_per_40ft_container=740, rate_per_reefer_container=1050,
        monthly_fixed_cost=40000, avg_revenue_per_call=100000,
        estimated_profit_margin=0.50,
    ),
    "BD3": BerthEconomics(
        berth_code="BD3", berth_class=BERTH_CLASS_PREMIUM, specialization="Oil_Tanker",
        base_operating_cost_per_hour=2500, rate_per_ton_oil_small=2500,
        rate_per_ton_oil_medium=4500, rate_per_ton_oil_large=7000,
        monthly_fixed_cost=75000, avg_revenue_per_call=5500,
        estimated_profit_margin=0.45, utilization_target_low=0.90,
        utilization_target_high=1.0, dp_high_premium=0.0, dp_low_discount=0.0,
    ),
    "BD2": BerthEconomics(
        berth_code="BD2", berth_class=BERTH_CLASS_STANDARD, specialization="Oil_Tanker",
        base_operating_cost_per_hour=2200, rate_per_ton_oil_small=2200,
        rate_per_ton_oil_medium=4000, rate_per_ton_oil_large=6500,
        monthly_fixed_cost=65000, avg_revenue_per_call=4500,
        estimated_profit_margin=0.40,
    ),
    "BD1": BerthEconomics(
        berth_code="BD1", berth_class=BERTH_CLASS_STANDARD, specialization="Oil_Tanker",
        base_operating_cost_per_hour=2000, rate_per_ton_oil_small=2000,
        rate_per_ton_oil_medium=3500, rate_per_ton_oil_large=6000,
        monthly_fixed_cost=60000, avg_revenue_per_call=4000,
        estimated_profit_margin=0.38,
    ),
    "C": BerthEconomics(
        berth_code="C", berth_class=BERTH_CLASS_PREMIUM, specialization="RoRo",
        base_operating_cost_per_hour=1200, rate_per_vehicle=75,
        monthly_fixed_cost=40000, avg_revenue_per_call=50000,
        estimated_profit_margin=0.60, utilization_target_low=0.75,
        utilization_target_high=0.85, dp_high_premium=0.10, dp_low_discount=0.15,
    ),
    "JD5": BerthEconomics(
        berth_code="JD5", berth_class=BERTH_CLASS_STANDARD, specialization="Multipurpose",
        base_operating_cost_per_hour=900, rate_per_ton_bulk=22,
        rate_per_ton_general=28, monthly_fixed_cost=25000,
        avg_revenue_per_call=60000, estimated_profit_margin=0.50,
    ),
    "JD6": BerthEconomics(
        berth_code="JD6", berth_class=BERTH_CLASS_STANDARD, specialization="Multipurpose",
        base_operating_cost_per_hour=900, rate_per_ton_bulk=22,
        rate_per_ton_general=28, monthly_fixed_cost=25000,
        avg_revenue_per_call=60000, estimated_profit_margin=0.50,
    ),
    "JD4": BerthEconomics(
        berth_code="JD4", berth_class=BERTH_CLASS_BUDGET, specialization="General",
        base_operating_cost_per_hour=700, rate_per_ton_general=20,
        monthly_fixed_cost=18000, avg_revenue_per_call=35000,
        estimated_profit_margin=0.40,
    ),
    "JD2": BerthEconomics(
        berth_code="JD2", berth_class=BERTH_CLASS_BUDGET, specialization="General",
        base_operating_cost_per_hour=700, rate_per_ton_general=20,
        monthly_fixed_cost=18000, avg_revenue_per_call=35000,
        estimated_profit_margin=0.40,
    ),
    "1 West": BerthEconomics(
        berth_code="1 West", berth_class=BERTH_CLASS_STANDARD, specialization="Chemical",
        base_operating_cost_per_hour=1100, rate_per_call_chemical=3500,
        monthly_fixed_cost=30000, avg_revenue_per_call=3500,
        estimated_profit_margin=0.40,
    ),
    "2 West": BerthEconomics(
        berth_code="2 West", berth_class=BERTH_CLASS_STANDARD, specialization="Chemical",
        base_operating_cost_per_hour=1100, rate_per_call_chemical=3500,
        monthly_fixed_cost=30000, avg_revenue_per_call=3500,
        estimated_profit_margin=0.40,
    ),
    "SCB1": BerthEconomics(
        berth_code="SCB1", berth_class=BERTH_CLASS_STANDARD, specialization="Container",
        base_operating_cost_per_hour=1100, rate_per_20ft_container=550,
        rate_per_40ft_container=720, monthly_fixed_cost=35000,
        avg_revenue_per_call=95000, estimated_profit_margin=0.48,
    ),
    "SCB2": BerthEconomics(
        berth_code="SCB2", berth_class=BERTH_CLASS_STANDARD, specialization="Container",
        base_operating_cost_per_hour=1100, rate_per_20ft_container=550,
        rate_per_40ft_container=720, monthly_fixed_cost=35000,
        avg_revenue_per_call=95000, estimated_profit_margin=0.48,
    ),
    "SCB3": BerthEconomics(
        berth_code="SCB3", berth_class=BERTH_CLASS_STANDARD, specialization="Container",
        base_operating_cost_per_hour=1150, rate_per_20ft_container=570,
        rate_per_40ft_container=740, monthly_fixed_cost=38000,
        avg_revenue_per_call=105000, estimated_profit_margin=0.49,
    ),
}


# ── Revenue Estimator ──────────────────────────────────────────────────────

@dataclass
class RevenueEstimate:
    berth_code: str
    vessel_type: str
    gross_revenue: float = 0.0
    operating_cost: float = 0.0
    profit: float = 0.0
    profit_margin: float = 0.0
    revenue_tier: str = ""       # HIGH / MEDIUM / LOW
    berth_class: str = ""
    rate_applied: float = 0.0
    rate_unit: str = ""
    dynamic_multiplier: float = 1.0
    partnership_discount: float = 0.0
    net_revenue: float = 0.0     # after discount


class BerthEconomicsCalculator:
    """
    Calculates revenue, cost, and profit for a vessel-berth pairing.

    Usage:
        calc = BerthEconomicsCalculator()
        estimate = calc.estimate_revenue(vessel_type="Container",
                                          berth_code="CTB3",
                                          cargo_quantity=200,
                                          service_hours=36)
    """

    def __init__(self, economics_db: Optional[Dict[str, BerthEconomics]] = None):
        self._db: Dict[str, BerthEconomics] = economics_db or {}
        # Always merge with defaults (DB takes priority)
        merged = dict(DEFAULT_BERTH_ECONOMICS)
        merged.update(self._db)
        self._db = merged

    def get_berth_economics(self, berth_code: str) -> BerthEconomics:
        """Return economics for a berth, fallback to default."""
        code = berth_code.strip()
        if code in self._db:
            return self._db[code]
        # Prefix matching (e.g. "CTB3 North" → "CTB3")
        for key, eco in self._db.items():
            if code.startswith(key):
                return eco
        # Return a generic budget berth if unknown
        return BerthEconomics(berth_code=code, berth_class=BERTH_CLASS_BUDGET)

    def estimate_revenue(
        self,
        vessel_type: str,
        berth_code: str,
        cargo_quantity: float = 0.0,    # containers, tons, or vehicles
        cargo_size: str = "20ft",       # 20ft / 40ft / reefer / small / medium / large
        service_hours: float = 24.0,
        current_utilization: float = 0.75,
        partnership_discount_pct: float = 0.0,
        dynamic_multiplier: float = 1.0,
    ) -> RevenueEstimate:
        """Estimate gross revenue, cost, and profit for a vessel-berth pair."""
        eco = self.get_berth_economics(berth_code)
        vtype = (vessel_type or "").strip().upper()

        # ── Revenue by vessel type ──────────────────────────────────────────
        if "CONTAINER" in vtype or eco.specialization == "Container":
            if "REEFER" in cargo_size.upper():
                rate = eco.rate_per_reefer_container
                unit = "reefer containers"
            elif "40" in cargo_size:
                rate = eco.rate_per_40ft_container
                unit = "40ft containers"
            else:
                rate = eco.rate_per_20ft_container
                unit = "20ft containers"
            qty = cargo_quantity or 100.0
            gross = rate * qty * dynamic_multiplier

        elif "TANKER" in vtype or "OIL" in vtype or eco.specialization == "Oil_Tanker":
            size_upper = (cargo_size or "").upper()
            if "LARGE" in size_upper or cargo_quantity > 40000:
                rate = eco.rate_per_ton_oil_large
            elif "MEDIUM" in size_upper or cargo_quantity > 15000:
                rate = eco.rate_per_ton_oil_medium
            else:
                rate = eco.rate_per_ton_oil_small
            qty = 1.0  # per-call
            unit = "per call (tanker)"
            gross = rate * dynamic_multiplier

        elif "RORO" in vtype or "RO-RO" in vtype or eco.specialization == "RoRo":
            rate = eco.rate_per_vehicle
            qty = cargo_quantity or 300.0
            unit = "vehicles"
            gross = rate * qty * dynamic_multiplier

        elif "CHEMICAL" in vtype or eco.specialization == "Chemical":
            rate = eco.rate_per_call_chemical
            qty = 1.0
            unit = "per call (chemical)"
            gross = rate * dynamic_multiplier

        elif "BULK" in vtype:
            rate = eco.rate_per_ton_bulk
            qty = cargo_quantity or 20000.0
            unit = "tons (bulk)"
            gross = rate * qty * dynamic_multiplier

        else:  # General cargo
            rate = eco.rate_per_ton_general
            qty = cargo_quantity or 10000.0
            unit = "tons (general)"
            gross = rate * qty * dynamic_multiplier

        # ── Operating cost ──────────────────────────────────────────────────
        operating_cost = eco.base_operating_cost_per_hour * service_hours

        # ── Partnership discount ────────────────────────────────────────────
        discount_amount = gross * (partnership_discount_pct / 100.0)
        net_revenue = gross - discount_amount

        # ── Profit ─────────────────────────────────────────────────────────
        profit = net_revenue - operating_cost
        margin = profit / net_revenue if net_revenue > 0 else 0.0

        # ── Revenue tier classification ─────────────────────────────────────
        if net_revenue >= 100_000:
            tier = "HIGH"
        elif net_revenue >= 50_000:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return RevenueEstimate(
            berth_code=berth_code,
            vessel_type=vessel_type,
            gross_revenue=round(gross, 2),
            operating_cost=round(operating_cost, 2),
            profit=round(profit, 2),
            profit_margin=round(margin, 4),
            revenue_tier=tier,
            berth_class=eco.berth_class,
            rate_applied=round(rate, 2),
            rate_unit=unit,
            dynamic_multiplier=round(dynamic_multiplier, 4),
            partnership_discount=round(discount_amount, 2),
            net_revenue=round(net_revenue, 2),
        )

    def commercial_score_for_berth(
        self,
        vessel_type: str,
        berth_code: str,
        cargo_quantity: float = 0.0,
        cargo_size: str = "20ft",
        service_hours: float = 24.0,
        current_utilization: float = 0.75,
        partnership_discount_pct: float = 0.0,
        dynamic_multiplier: float = 1.0,
        max_expected_revenue: float = 120_000.0,
    ) -> float:
        """
        Return a normalized commercial score 0-100 for this vessel-berth pair.
        Higher = more commercially attractive.
        """
        est = self.estimate_revenue(
            vessel_type=vessel_type,
            berth_code=berth_code,
            cargo_quantity=cargo_quantity,
            cargo_size=cargo_size,
            service_hours=service_hours,
            current_utilization=current_utilization,
            partnership_discount_pct=partnership_discount_pct,
            dynamic_multiplier=dynamic_multiplier,
        )

        # Revenue component (0-60): normalized against max expected revenue
        rev_score = min(60.0, (est.net_revenue / max(max_expected_revenue, 1)) * 60)

        # Margin component (0-25): perfect margin = 25
        margin_score = min(25.0, est.profit_margin * 50)

        # Berth class bonus (0-15)
        class_bonus = {
            BERTH_CLASS_PREMIUM: 15.0,
            BERTH_CLASS_STANDARD: 8.0,
            BERTH_CLASS_BUDGET: 2.0,
        }.get(est.berth_class, 5.0)

        total = rev_score + margin_score + class_bonus
        return round(min(100.0, max(0.0, total)), 2)

    def list_all_economics(self) -> Dict[str, BerthEconomics]:
        return dict(self._db)
