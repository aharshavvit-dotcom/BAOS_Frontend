"""
Dynamic Pricing Engine
Adjusts berth rates based on:
  - Utilization (demand-based)
  - Time of day (peak/off-peak)
  - Day of week (weekend discount)
  - Season (quarterly adjustments)
  - Hazmat premium for oil/chemical berths
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PricingAdjustment:
    base_multiplier: float = 1.0
    utilization_factor: float = 1.0
    time_of_day_factor: float = 1.0
    day_of_week_factor: float = 1.0
    seasonal_factor: float = 1.0
    hazmat_factor: float = 1.0
    final_multiplier: float = 1.0
    adjustment_reason: str = ""


class DynamicPricingEngine:
    """
    Computes a pricing multiplier for a specific berth+time combination.

    Rules:
      Utilization > 90%  → +15% premium
      Utilization 75-90% → +5%
      Utilization 50-75% → standard
      Utilization < 50%  → -10% discount

      Off-peak (18:00-06:00) → -20% (except oil berths)
      Weekend → -30% (except oil berths)

      Q4 (Oct-Dec) containers → +10%
      Q1 (Jan-Mar) containers → -10%
      Winter (Dec-Feb) oil    → +10%
      Summer (Jun-Aug) oil    → -5%

      Hazmat (oil/chemical)   → +25% surcharge on applicable berths
    """

    # Berths that use fixed pricing (safety reasons, no dynamic adjustments)
    FIXED_PRICE_BERTHS = {"BD1", "BD2", "BD3", "1 West", "2 West"}

    def compute(
        self,
        berth_code: str,
        specialization: str = "General",
        current_utilization: float = 0.75,
        arrival_dt: Optional[datetime] = None,
        is_hazmat: bool = False,
    ) -> PricingAdjustment:
        """
        Compute the pricing multiplier for a berth at a given time.

        Args:
            berth_code: Berth identifier
            specialization: Berth type (Container, Oil_Tanker, Chemical, etc.)
            current_utilization: Current utilization 0.0-1.0
            arrival_dt: Arrival datetime (defaults to now)
            is_hazmat: Whether vessel carries hazardous materials

        Returns:
            PricingAdjustment with final_multiplier (apply to base rate)
        """
        adj = PricingAdjustment()
        spec_upper = specialization.upper()
        is_fixed = berth_code in self.FIXED_PRICE_BERTHS or "OIL" in spec_upper

        # ── 1. Utilization-based adjustment ──────────────────────────────
        if not is_fixed:
            if current_utilization >= 0.90:
                adj.utilization_factor = 1.15
            elif current_utilization >= 0.75:
                adj.utilization_factor = 1.05
            elif current_utilization < 0.50:
                adj.utilization_factor = 0.90
            else:
                adj.utilization_factor = 1.00

        # ── 2. Time of day adjustment ─────────────────────────────────────
        dt = arrival_dt or datetime.now()
        hour = dt.hour
        weekday = dt.weekday()  # 0=Mon, 6=Sun

        if not is_fixed:
            if hour < 6 or hour >= 18:
                adj.time_of_day_factor = 0.80   # off-peak discount 20%
            else:
                adj.time_of_day_factor = 1.00   # peak hours standard

        # ── 3. Weekend adjustment ─────────────────────────────────────────
        if not is_fixed and weekday >= 5:  # Sat / Sun
            adj.day_of_week_factor = 0.70   # -30% weekend discount

        # ── 4. Seasonal adjustment ────────────────────────────────────────
        month = dt.month
        if "CONTAINER" in spec_upper:
            if month in (10, 11, 12):     # Q4 year-end rush
                adj.seasonal_factor = 1.10
            elif month in (1, 2, 3):      # Q1 slowdown
                adj.seasonal_factor = 0.90
        elif is_fixed and "OIL" in spec_upper:
            if month in (12, 1, 2):       # Winter heating demand
                adj.seasonal_factor = 1.10
            elif month in (6, 7, 8):      # Summer lower demand
                adj.seasonal_factor = 0.95

        # ── 5. Hazmat premium ─────────────────────────────────────────────
        if is_hazmat:
            adj.hazmat_factor = 1.25      # 25% hazmat surcharge

        # ── 6. Combine factors ────────────────────────────────────────────
        adj.final_multiplier = round(
            adj.utilization_factor
            * adj.time_of_day_factor
            * adj.day_of_week_factor
            * adj.seasonal_factor
            * adj.hazmat_factor,
            4,
        )
        adj.base_multiplier = 1.0

        # ── 7. Human-readable reason ──────────────────────────────────────
        reasons = []
        if adj.utilization_factor > 1.0:
            reasons.append(f"High demand +{(adj.utilization_factor-1)*100:.0f}%")
        elif adj.utilization_factor < 1.0:
            reasons.append(f"Low demand {(adj.utilization_factor-1)*100:.0f}%")
        if adj.time_of_day_factor < 1.0:
            reasons.append(f"Off-peak −{(1-adj.time_of_day_factor)*100:.0f}%")
        if adj.day_of_week_factor < 1.0:
            reasons.append(f"Weekend −{(1-adj.day_of_week_factor)*100:.0f}%")
        if adj.seasonal_factor != 1.0:
            sign = "+" if adj.seasonal_factor > 1 else "−"
            reasons.append(f"Seasonal {sign}{abs(adj.seasonal_factor-1)*100:.0f}%")
        if adj.hazmat_factor > 1.0:
            reasons.append(f"Hazmat +{(adj.hazmat_factor-1)*100:.0f}%")
        if is_fixed:
            reasons.append("Fixed pricing (safety)")

        adj.adjustment_reason = "; ".join(reasons) if reasons else "Standard pricing"
        return adj

    def get_pricing_summary(
        self,
        berth_code: str,
        specialization: str = "General",
        current_utilization: float = 0.75,
    ) -> dict:
        """Return a summary dict of current pricing factors (for UI display)."""
        adj = self.compute(berth_code, specialization, current_utilization)
        return {
            "berth_code": berth_code,
            "final_multiplier": adj.final_multiplier,
            "adjustment_pct": round((adj.final_multiplier - 1) * 100, 1),
            "reason": adj.adjustment_reason,
            "utilization": f"{current_utilization*100:.0f}%",
            "is_premium": adj.final_multiplier > 1.05,
            "is_discounted": adj.final_multiplier < 0.95,
        }
