"""
Commercial Repository — CRUD operations for commercial intelligence data.
Provides in-memory fallback when DB is unavailable.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from db.connection import get_connection
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

from commercial_engine.berth_economics import BerthEconomics, DEFAULT_BERTH_ECONOMICS
from commercial_engine.partnership_manager import (
    VesselCompany, PartnershipTier, ContractObligation, DEFAULT_PARTNERSHIPS
)


# ── Berth Economics ────────────────────────────────────────────────────────

def get_all_berth_economics() -> Dict[str, BerthEconomics]:
    """Fetch berth economics from DB, fall back to defaults."""
    if not DB_AVAILABLE:
        return dict(DEFAULT_BERTH_ECONOMICS)
    try:
        rows = {}
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT berth_code, berth_class, specialization, base_operating_cost_ph, "
                            "rate_20ft_container, rate_40ft_container, rate_reefer_container, "
                            "rate_ton_bulk, rate_ton_general, rate_oil_small, rate_oil_medium, rate_oil_large, "
                            "rate_vehicle, rate_chemical_call, monthly_fixed_cost, avg_revenue_per_call, "
                            "profit_margin_est, utilization_target_low, utilization_target_high, "
                            "dp_high_threshold, dp_low_threshold, dp_high_premium, dp_low_discount "
                            "FROM berth_economics ORDER BY berth_code")
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    r = dict(zip(cols, row))
                    eco = BerthEconomics(
                        berth_code=r["berth_code"],
                        berth_class=r["berth_class"],
                        specialization=r["specialization"],
                        base_operating_cost_per_hour=float(r["base_operating_cost_ph"] or 900),
                        rate_per_20ft_container=float(r["rate_20ft_container"] or 600),
                        rate_per_40ft_container=float(r["rate_40ft_container"] or 800),
                        rate_per_reefer_container=float(r["rate_reefer_container"] or 1200),
                        rate_per_ton_bulk=float(r["rate_ton_bulk"] or 22),
                        rate_per_ton_general=float(r["rate_ton_general"] or 28),
                        rate_per_ton_oil_small=float(r["rate_oil_small"] or 2500),
                        rate_per_ton_oil_medium=float(r["rate_oil_medium"] or 4500),
                        rate_per_ton_oil_large=float(r["rate_oil_large"] or 7000),
                        rate_per_vehicle=float(r["rate_vehicle"] or 75),
                        rate_per_call_chemical=float(r["rate_chemical_call"] or 3500),
                        monthly_fixed_cost=float(r["monthly_fixed_cost"] or 30000),
                        avg_revenue_per_call=float(r["avg_revenue_per_call"] or 60000),
                        estimated_profit_margin=float(r["profit_margin_est"] or 0.45),
                        utilization_target_low=float(r["utilization_target_low"] or 0.70),
                        utilization_target_high=float(r["utilization_target_high"] or 0.85),
                        dp_high_utilization=float(r["dp_high_threshold"] or 0.90),
                        dp_low_utilization=float(r["dp_low_threshold"] or 0.50),
                        dp_high_premium=float(r["dp_high_premium"] or 0.15),
                        dp_low_discount=float(r["dp_low_discount"] or 0.10),
                    )
                    rows[r["berth_code"]] = eco
        # Merge with defaults (DB takes priority)
        merged = dict(DEFAULT_BERTH_ECONOMICS)
        for k, v in rows.items():
            merged[str(k)] = v
        return merged
    except Exception as e:
        print(f"[CommercialRepo] DB fetch failed, using defaults: {e}", file=sys.stderr)
        return dict(DEFAULT_BERTH_ECONOMICS)


# ── Vessel Companies ───────────────────────────────────────────────────────

def get_all_companies() -> Dict[str, VesselCompany]:
    """Fetch vessel companies + contract obligations from DB, fall back to defaults."""
    if not DB_AVAILABLE:
        return dict(DEFAULT_PARTNERSHIPS)
    try:
        companies: Dict[str, VesselCompany] = {}
        obligations: Dict[str, ContractObligation] = {}

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Companies
                cur.execute("""
                    SELECT company_id, display_name, tier, annual_contract_value, visits_per_year,
                           contract_start, contract_expiry, is_contract, discount_percentage,
                           discount_reason, additional_benefits, contact_person, contact_title,
                           email, phone, notes
                    FROM vessel_companies ORDER BY company_id
                """)
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    r = dict(zip(cols, row))
                    try:
                        tier = PartnershipTier(r["tier"])
                    except ValueError:
                        tier = PartnershipTier.STANDARD
                    vc = VesselCompany(
                        company_id=r["company_id"],
                        display_name=r["display_name"],
                        tier=tier,
                        annual_contract_value=float(r["annual_contract_value"]) if r.get("annual_contract_value") else 0.0,
                        visits_per_year=int(r["visits_per_year"]) if r.get("visits_per_year") else 0,
                        contract_start=r["contract_start"],
                        contract_expiry=r["contract_expiry"],
                        is_contract=bool(r["is_contract"]),
                        discount_percentage=float(r["discount_percentage"]) if r.get("discount_percentage") else 0.0,
                        discount_reason=r.get("discount_reason") or "",
                        additional_benefits=[x for x in (r.get("additional_benefits") or [])],
                        contact_person=r["contact_person"] or "",
                        contact_title=r["contact_title"] or "",
                        email=r["email"] or "",
                        phone=r["phone"] or "",
                        notes=r["notes"] or "",
                    )
                    companies[r["company_id"]] = vc

                # Contract obligations
                cur.execute("""
                    SELECT company_id, guaranteed_berth_types, guaranteed_slots_month,
                           priority_level, sla_turnaround_hours
                    FROM contract_obligations
                """)
                for row in cur.fetchall():
                    ob = ContractObligation(
                        guaranteed_berth_types=list(row[1] or []),
                        guaranteed_slots_per_month=int(row[2] or 0),
                        priority_level=int(row[3] or 4),
                        sla_turnaround_hours=float(row[4] or 48),
                    )
                    if row[0] in companies:
                        companies[row[0]].contract_obligations = ob

        # Merge with defaults
        merged = dict(DEFAULT_PARTNERSHIPS)
        for k, v in companies.items():
            merged[k] = v
        return merged
    except Exception as e:
        print(f"[CommercialRepo] DB fetch failed, using defaults: {e}", file=sys.stderr)
        return dict(DEFAULT_PARTNERSHIPS)


def upsert_company(company: VesselCompany) -> bool:
    """Insert or update a company record in the DB."""
    if not DB_AVAILABLE:
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vessel_companies (
                        company_id, display_name, tier, annual_contract_value, visits_per_year,
                        contract_start, contract_expiry, is_contract, discount_percentage,
                        discount_reason, additional_benefits, contact_person, contact_title,
                        email, phone, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (company_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        tier = EXCLUDED.tier,
                        discount_percentage = EXCLUDED.discount_percentage,
                        annual_contract_value = EXCLUDED.annual_contract_value,
                        contract_expiry = EXCLUDED.contract_expiry,
                        updated_at = NOW()
                """, (
                    company.company_id, company.display_name, company.tier.value,
                    company.annual_contract_value, company.visits_per_year,
                    company.contract_start, company.contract_expiry,
                    company.is_contract, company.discount_percentage,
                    company.discount_reason, company.additional_benefits,
                    company.contact_person, company.contact_title,
                    company.email, company.phone, company.notes,
                ))
        return True
    except Exception as e:
        print(f"[CommercialRepo] Upsert failed: {e}", file=sys.stderr)
        return False


# ── Assignment Logging ─────────────────────────────────────────────────────

def log_commercial_assignment(
    vessel_id: str,
    vessel_name: str,
    berth_code: str,
    vessel_company: str,
    vessel_type: str,
    partnership_tier: str,
    predicted_revenue: float,
    discount_applied_pct: float = 0.0,
    dynamic_multiplier: float = 1.0,
    decision_mode: str = "balanced",
) -> bool:
    """Log a new commercial assignment for learning engine."""
    if not DB_AVAILABLE:
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO commercial_assignments (
                        vessel_id, vessel_name, berth_code, vessel_company, vessel_type,
                        partnership_tier, predicted_revenue, discount_applied_pct,
                        dynamic_multiplier, decision_mode
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    vessel_id, vessel_name, berth_code, vessel_company, vessel_type,
                    partnership_tier, predicted_revenue, discount_applied_pct,
                    dynamic_multiplier, decision_mode,
                ))
        return True
    except Exception as e:
        print(f"[CommercialRepo] Log failed: {e}", file=sys.stderr)
        return False


def get_recent_assignments(limit: int = 50) -> List[dict]:
    """Fetch recent commercial assignments for the learning dashboard."""
    if not DB_AVAILABLE:
        return []
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT vessel_name, berth_code, vessel_company, partnership_tier,
                           predicted_revenue, discount_applied_pct, dynamic_multiplier,
                           decision_mode, assignment_dt
                    FROM commercial_assignments
                    ORDER BY assignment_dt DESC LIMIT %s
                """, (limit,))
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        print(f"[CommercialRepo] Fetch failed: {e}", file=sys.stderr)
        return []
