"""
Seed Data — Populates the ML_APP database with default commercial intelligence data.
Run once after schema creation or to refresh with default data.

Usage:
    python db/seed_data.py
    # or from project root:
    python -m db.seed_data
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from db.connection import get_connection, test_connection
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


def run_schema(conn) -> None:
    """Execute the schema SQL."""
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    sql = schema_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    print("  ✓ Schema created (tables dropped + recreated)")


def seed_berth_economics(conn) -> int:
    """Insert berth economics seed data."""
    berths = [
        ("CTB3",  "Container Terminal Berth 3",  "PREMIUM",  "Container",    1500, 600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 50000, 120000, 0.55, 0.80, 0.90, 0.90, 0.50, 0.15, 0.10),
        ("CTB2",  "Container Terminal Berth 2",  "STANDARD", "Container",    1200, 580, 760, 1100, 22, 28, 2200, 4000, 6500, 75, 3500, 40000, 100000, 0.50, 0.75, 0.85, 0.90, 0.50, 0.12, 0.10),
        ("CTB1",  "Container Terminal Berth 1",  "STANDARD", "Container",    1200, 560, 740, 1050, 22, 28, 2000, 3500, 6000, 75, 3500, 40000, 100000, 0.50, 0.75, 0.85, 0.90, 0.50, 0.12, 0.10),
        ("BD3",   "Oil/Bulk Jetty 3",            "PREMIUM",  "Oil_Tanker",   2500, 600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 75000,   5500, 0.45, 0.90, 1.00, 0.90, 0.50, 0.00, 0.00),
        ("BD2",   "Oil/Bulk Jetty 2",            "STANDARD", "Oil_Tanker",   2200, 600, 800, 1200, 22, 28, 2200, 4000, 6500, 75, 3500, 65000,   4500, 0.40, 0.85, 0.95, 0.90, 0.50, 0.00, 0.00),
        ("BD1",   "Oil/Bulk Jetty 1",            "STANDARD", "Oil_Tanker",   2000, 600, 800, 1200, 22, 28, 2000, 3500, 6000, 75, 3500, 60000,   4000, 0.38, 0.80, 0.95, 0.90, 0.50, 0.00, 0.00),
        ("C",     "RoRo Berth C",                "PREMIUM",  "RoRo",         1200, 600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 40000,  50000, 0.60, 0.75, 0.85, 0.90, 0.50, 0.10, 0.15),
        ("JD5",   "Jawahar Dock 5",              "STANDARD", "Multipurpose", 900,  600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 25000,  60000, 0.50, 0.70, 0.80, 0.90, 0.50, 0.12, 0.12),
        ("JD6",   "Jawahar Dock 6",              "STANDARD", "Multipurpose", 900,  600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 25000,  60000, 0.50, 0.70, 0.80, 0.90, 0.50, 0.12, 0.12),
        ("JD4",   "Jawahar Dock 4",              "BUDGET",   "General",      700,  600, 800, 1200, 22, 20, 2500, 4500, 7000, 75, 3500, 18000,  35000, 0.40, 0.60, 0.75, 0.90, 0.50, 0.10, 0.10),
        ("JD2",   "Jawahar Dock 2",              "BUDGET",   "General",      700,  600, 800, 1200, 22, 20, 2500, 4500, 7000, 75, 3500, 18000,  35000, 0.40, 0.60, 0.75, 0.90, 0.50, 0.10, 0.10),
        ("1 West","West Quay 1",                 "STANDARD", "Chemical",     1100, 600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 30000,   3500, 0.40, 0.70, 0.85, 0.90, 0.50, 0.12, 0.12),
        ("2 West","West Quay 2",                 "STANDARD", "Chemical",     1100, 600, 800, 1200, 22, 28, 2500, 4500, 7000, 75, 3500, 30000,   3500, 0.40, 0.70, 0.85, 0.90, 0.50, 0.12, 0.12),
        ("SCB1",  "South Container Berth 1",     "STANDARD", "Container",    1100, 550, 720, 1000, 22, 28, 2200, 4000, 6500, 75, 3500, 35000,  95000, 0.48, 0.75, 0.85, 0.90, 0.50, 0.12, 0.10),
        ("SCB2",  "South Container Berth 2",     "STANDARD", "Container",    1100, 550, 720, 1000, 22, 28, 2200, 4000, 6500, 75, 3500, 35000,  95000, 0.48, 0.75, 0.85, 0.90, 0.50, 0.12, 0.10),
        ("SCB3",  "South Container Berth 3",     "STANDARD", "Container",    1150, 570, 740, 1050, 22, 28, 2200, 4000, 6500, 75, 3500, 38000, 105000, 0.49, 0.75, 0.85, 0.90, 0.50, 0.12, 0.10),
    ]
    sql = """
        INSERT INTO berth_economics (
            berth_code, berth_name, berth_class, specialization,
            base_operating_cost_ph, rate_20ft_container, rate_40ft_container,
            rate_reefer_container, rate_ton_bulk, rate_ton_general,
            rate_oil_small, rate_oil_medium, rate_oil_large,
            rate_vehicle, rate_chemical_call,
            monthly_fixed_cost, avg_revenue_per_call, profit_margin_est,
            utilization_target_low, utilization_target_high,
            dp_high_threshold, dp_low_threshold, dp_high_premium, dp_low_discount
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (berth_code) DO UPDATE SET
            berth_class = EXCLUDED.berth_class,
            base_operating_cost_ph = EXCLUDED.base_operating_cost_ph,
            avg_revenue_per_call = EXCLUDED.avg_revenue_per_call,
            updated_at = NOW()
    """
    with conn.cursor() as cur:
        for row in berths:
            cur.execute(sql, row)
    print(f"  ✓ Seeded {len(berths)} berth economics records")
    return len(berths)


def seed_vessel_companies(conn) -> int:
    """Insert partnership seed data."""
    companies = [
        {
            "company_id": "MAERSK",
            "display_name": "Maersk Line",
            "tier": "VIP",
            "annual_contract_value": 8500000,
            "visits_per_year": 95,
            "contract_start": "2018-06-01",
            "contract_expiry": "2028-06-01",
            "is_contract": True,
            "discount_percentage": 15.0,
            "discount_reason": "Long-term volume commitment",
            "additional_benefits": ["Priority berthing", "Fast-track documentation", "Quarterly business review"],
            "contact_person": "John Smith",
            "contact_title": "VP Port Operations",
            "email": "john.smith@maersk.com",
            "phone": "+45-1234-5678",
            "notes": "",
            "guaranteed_berths": ["CTB1", "CTB2", "CTB3"],
            "slots_month": 8,
            "priority_level": 1,
            "sla_hours": 36.0,
        },
        {
            "company_id": "SHELL",
            "display_name": "Shell Tanker Operations",
            "tier": "VIP",
            "annual_contract_value": 6200000,
            "visits_per_year": 45,
            "contract_start": "2015-01-01",
            "contract_expiry": "2025-01-01",
            "is_contract": True,
            "discount_percentage": 12.0,
            "discount_reason": "Strategic long-term partnership",
            "additional_benefits": ["Dedicated hazmat berth", "Custom scheduling"],
            "contact_person": "Sarah Johnson",
            "contact_title": "Supply Manager",
            "email": "sarah.johnson@shell.com",
            "phone": "+1-713-5678-9012",
            "notes": "",
            "guaranteed_berths": ["BD1", "BD2", "BD3"],
            "slots_month": 4,
            "priority_level": 1,
            "sla_hours": 48.0,
        },
        {
            "company_id": "ONE",
            "display_name": "Ocean Network Express",
            "tier": "PREMIUM",
            "annual_contract_value": 3200000,
            "visits_per_year": 24,
            "contract_start": "2020-03-01",
            "contract_expiry": "2026-03-01",
            "is_contract": True,
            "discount_percentage": 8.0,
            "discount_reason": "Growth partnership",
            "additional_benefits": ["Priority from top-3 berths"],
            "contact_person": "David Lee",
            "contact_title": "Regional Manager",
            "email": "david.lee@one-line.com",
            "phone": "",
            "notes": "",
            "guaranteed_berths": ["CTB1", "CTB2", "SCB1", "SCB2"],
            "slots_month": 2,
            "priority_level": 2,
            "sla_hours": 40.0,
        },
        {
            "company_id": "MSC_EXPANSION",
            "display_name": "MSC (Expansion Program)",
            "tier": "STRATEGIC_PROSPECT",
            "annual_contract_value": 0,
            "visits_per_year": 0,
            "contract_start": "2025-01-01",
            "contract_expiry": None,
            "is_contract": False,
            "discount_percentage": 20.0,
            "discount_reason": "Acquisition incentive",
            "additional_benefits": ["Best available berth", "Executive management", "Dedicated contact"],
            "contact_person": "Anna Mueller",
            "contact_title": "VP Port Operations",
            "email": "anna.mueller@msc.com",
            "phone": "",
            "notes": "Trial period 6 months → upgrade to PREMIUM if successful",
            "guaranteed_berths": [],
            "slots_month": 0,
            "priority_level": 2,
            "sla_hours": 40.0,
        },
        {
            "company_id": "SPOT_MARKET",
            "display_name": "Spot Market / Walk-in",
            "tier": "STANDARD",
            "annual_contract_value": 0,
            "visits_per_year": 0,
            "contract_start": None,
            "contract_expiry": None,
            "is_contract": False,
            "discount_percentage": 0.0,
            "discount_reason": "",
            "additional_benefits": [],
            "contact_person": "Operations Desk",
            "contact_title": "Duty Officer",
            "email": "",
            "phone": "",
            "notes": "Default for unrecognized vessel companies",
            "guaranteed_berths": [],
            "slots_month": 0,
            "priority_level": 4,
            "sla_hours": 72.0,
        },
    ]

    vc_sql = """
        INSERT INTO vessel_companies (
            company_id, display_name, tier, annual_contract_value, visits_per_year,
            contract_start, contract_expiry, is_contract, discount_percentage,
            discount_reason, additional_benefits, contact_person, contact_title,
            email, phone, notes
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (company_id) DO UPDATE SET
            tier = EXCLUDED.tier,
            discount_percentage = EXCLUDED.discount_percentage,
            updated_at = NOW()
    """
    ob_sql = """
        INSERT INTO contract_obligations (
            company_id, guaranteed_berth_types, guaranteed_slots_month,
            priority_level, sla_turnaround_hours
        ) VALUES (%s,%s,%s,%s,%s)
    """

    with conn.cursor() as cur:
        for c in companies:
            cur.execute(vc_sql, (
                c["company_id"], c["display_name"], c["tier"],
                c["annual_contract_value"], c["visits_per_year"],
                c["contract_start"], c["contract_expiry"],
                c["is_contract"], c["discount_percentage"],
                c["discount_reason"], c["additional_benefits"],
                c["contact_person"], c["contact_title"],
                c["email"], c["phone"], c["notes"],
            ))
            cur.execute(ob_sql, (
                c["company_id"], c["guaranteed_berths"],
                c["slots_month"], c["priority_level"], c["sla_hours"],
            ))

    print(f"  ✓ Seeded {len(companies)} vessel companies with contract obligations")
    return len(companies)


def seed_pricing_rules(conn) -> int:
    """Insert default pricing rules."""
    rules = [
        ("Container Berths Dynamic Pricing", "Container",
         0.90, 0.50, 15.0, 10.0, 20.0, 30.0, 10.0, 10.0, 0.0),
        ("Oil Berths Fixed Pricing", "Oil_Tanker",
         1.00, 0.00, 0.0,  0.0,  0.0,  0.0,  10.0, 0.0, 25.0),
        ("General/Multipurpose Dynamic Pricing", "ALL",
         0.90, 0.50, 12.0, 12.0, 20.0, 30.0, 5.0,  5.0, 0.0),
    ]
    sql = """
        INSERT INTO pricing_rules (
            rule_name, berth_type, utilization_high, utilization_low,
            premium_pct, discount_pct, off_peak_discount_pct, weekend_discount_pct,
            q4_premium_pct, q1_discount_pct, hazmat_premium_pct
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    with conn.cursor() as cur:
        for row in rules:
            cur.execute(sql, row)
    print(f"  ✓ Seeded {len(rules)} pricing rules")
    return len(rules)


def main():
    print("\n🌊 BAOS AI — Commercial Intelligence DB Seeder")
    print("=" * 50)

    if not DB_AVAILABLE:
        print("❌ DB module unavailable (psycopg2 not installed?)")
        return

    print(f"  Connecting to localhost:5433/ML_APP ...")
    if not test_connection():
        print("❌ Cannot connect to database. Check credentials and that PostgreSQL is running.")
        return

    print("  ✓ Connected!")
    print()

    try:
        with get_connection() as conn:
            print("📐 Creating schema ...")
            run_schema(conn)
            print("\n🏗️  Seeding data ...")
            n_berths = seed_berth_economics(conn)
            n_companies = seed_vessel_companies(conn)
            n_rules = seed_pricing_rules(conn)

        print(f"\n✅ Done! Seeded {n_berths} berths, {n_companies} companies, {n_rules} pricing rules.")
        print("   Commercial Intelligence Layer is ready.\n")

    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        raise


if __name__ == "__main__":
    main()
