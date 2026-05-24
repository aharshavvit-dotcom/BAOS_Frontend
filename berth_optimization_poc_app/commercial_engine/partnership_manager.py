"""
Partnership Manager
Vessel company tier classification, discount calculation, SLA obligation tracking.
Supports VIP, PREMIUM, STANDARD, and STRATEGIC_PROSPECT tiers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional


# ── Tier Definitions ───────────────────────────────────────────────────────

class PartnershipTier(str, Enum):
    VIP = "VIP"
    PREMIUM = "PREMIUM"
    STANDARD = "STANDARD"
    STRATEGIC_PROSPECT = "STRATEGIC_PROSPECT"


TIER_PRIORITY = {
    PartnershipTier.VIP: 1,
    PartnershipTier.STRATEGIC_PROSPECT: 2,   # Red-carpet treatment
    PartnershipTier.PREMIUM: 3,
    PartnershipTier.STANDARD: 4,
}

TIER_COLORS = {
    PartnershipTier.VIP: "#f59e0b",              # Gold
    PartnershipTier.STRATEGIC_PROSPECT: "#8b5cf6", # Purple
    PartnershipTier.PREMIUM: "#0ea5e9",           # Sky Blue
    PartnershipTier.STANDARD: "#64748b",           # Slate
}

TIER_BADGES = {
    PartnershipTier.VIP: "👑 VIP",
    PartnershipTier.STRATEGIC_PROSPECT: "⭐ STRATEGIC PROSPECT",
    PartnershipTier.PREMIUM: "💎 PREMIUM",
    PartnershipTier.STANDARD: "📦 STANDARD",
}


@dataclass
class ContractObligation:
    guaranteed_berth_types: List[str] = field(default_factory=list)
    guaranteed_slots_per_month: int = 0
    priority_level: int = 4
    sla_turnaround_hours: float = 48.0


@dataclass
class VesselCompany:
    company_id: str
    display_name: str
    tier: PartnershipTier = PartnershipTier.STANDARD
    annual_contract_value: float = 0.0
    visits_per_year: int = 0
    contract_start: Optional[date] = None
    contract_expiry: Optional[date] = None
    is_contract: bool = False
    discount_percentage: float = 0.0
    discount_reason: str = ""
    additional_benefits: List[str] = field(default_factory=list)
    contact_person: str = ""
    contact_title: str = ""
    email: str = ""
    phone: str = ""
    contract_obligations: Optional[ContractObligation] = None
    notes: str = ""

    @property
    def is_contract_active(self) -> bool:
        if not self.is_contract or self.contract_expiry is None:
            return False
        return self.contract_expiry >= date.today()

    @property
    def priority(self) -> int:
        return TIER_PRIORITY.get(self.tier, 4)

    @property
    def tier_badge(self) -> str:
        return TIER_BADGES.get(self.tier, "📦 STANDARD")

    @property
    def tier_color(self) -> str:
        return TIER_COLORS.get(self.tier, "#64748b")


# ── Default Partnership Database ───────────────────────────────────────────

DEFAULT_PARTNERSHIPS: Dict[str, VesselCompany] = {
    "MAERSK": VesselCompany(
        company_id="MAERSK",
        display_name="Maersk Line",
        tier=PartnershipTier.VIP,
        annual_contract_value=8_500_000,
        visits_per_year=95,
        contract_start=date(2018, 6, 1),
        contract_expiry=date(2028, 6, 1),
        is_contract=True,
        discount_percentage=15.0,
        discount_reason="Long-term volume commitment",
        additional_benefits=[
            "Priority berthing at CTB1/CTB2/CTB3",
            "Fast-track documentation (1h)",
            "Quarterly business reviews",
            "Dedicated berth during monsoon",
        ],
        contact_person="John Smith",
        contact_title="VP Port Operations",
        email="john.smith@maersk.com",
        phone="+45-1234-5678",
        contract_obligations=ContractObligation(
            guaranteed_berth_types=["CTB1", "CTB2", "CTB3"],
            guaranteed_slots_per_month=8,
            priority_level=1,
            sla_turnaround_hours=36.0,
        ),
    ),
    "SHELL": VesselCompany(
        company_id="SHELL",
        display_name="Shell Tanker Operations",
        tier=PartnershipTier.VIP,
        annual_contract_value=6_200_000,
        visits_per_year=45,
        contract_start=date(2015, 1, 1),
        contract_expiry=date(2025, 1, 1),
        is_contract=True,
        discount_percentage=12.0,
        discount_reason="Strategic long-term partnership",
        additional_benefits=[
            "Dedicated hazmat berth access",
            "Custom scheduling window",
            "Priority pilot assignment",
        ],
        contact_person="Sarah Johnson",
        contact_title="Supply Manager",
        email="sarah.johnson@shell.com",
        phone="+1-713-5678-9012",
        contract_obligations=ContractObligation(
            guaranteed_berth_types=["BD1", "BD2", "BD3"],
            guaranteed_slots_per_month=4,
            priority_level=1,
            sla_turnaround_hours=48.0,
        ),
    ),
    "ONE": VesselCompany(
        company_id="ONE",
        display_name="Ocean Network Express",
        tier=PartnershipTier.PREMIUM,
        annual_contract_value=3_200_000,
        visits_per_year=24,
        contract_start=date(2020, 3, 1),
        contract_expiry=date(2026, 3, 1),
        is_contract=True,
        discount_percentage=8.0,
        discount_reason="Growth partnership",
        additional_benefits=[
            "Priority selection from top-3 berths",
            "Dedicated account manager",
        ],
        contact_person="David Lee",
        contact_title="Regional Manager",
        email="david.lee@one-line.com",
        contract_obligations=ContractObligation(
            guaranteed_berth_types=["CTB1", "CTB2", "SCB1", "SCB2"],
            guaranteed_slots_per_month=2,
            priority_level=2,
            sla_turnaround_hours=40.0,
        ),
    ),
    "MSC_EXPANSION": VesselCompany(
        company_id="MSC_EXPANSION",
        display_name="MSC (Expansion Program)",
        tier=PartnershipTier.STRATEGIC_PROSPECT,
        annual_contract_value=0,
        visits_per_year=0,
        contract_start=date(2025, 1, 1),
        is_contract=False,
        discount_percentage=20.0,
        discount_reason="Acquisition incentive — first-call discount",
        additional_benefits=[
            "Best available berth always",
            "Executive relationship management",
            "Dedicated senior contact",
            "Fast-track service (2h vs 4h)",
        ],
        contact_person="Anna Mueller",
        contact_title="VP Port Operations",
        email="anna.mueller@msc.com",
        contract_obligations=ContractObligation(
            guaranteed_berth_types=[],
            guaranteed_slots_per_month=0,
            priority_level=2,
            sla_turnaround_hours=40.0,
        ),
        notes="Trial period 6 months → upgrade to PREMIUM if successful",
    ),
    "SPOT_MARKET": VesselCompany(
        company_id="SPOT_MARKET",
        display_name="Spot Market / Walk-in",
        tier=PartnershipTier.STANDARD,
        annual_contract_value=0,
        visits_per_year=0,
        is_contract=False,
        discount_percentage=0.0,
        discount_reason="",
        contact_person="Operations Desk",
        contact_title="Duty Officer",
    ),
}

# Alias/name mapping (vessel company names that map to canonical IDs)
COMPANY_ALIASES: Dict[str, str] = {
    "MAERSK SEALAND": "MAERSK",
    "MAERSK CONTAINER": "MAERSK",
    "MAERSK LINE": "MAERSK",
    "AP MOLLER": "MAERSK",
    "AP MOLLER MAERSK": "MAERSK",
    "SHELL": "SHELL",
    "SHELL TANKER": "SHELL",
    "ONE LINE": "ONE",
    "OCEAN NETWORK": "ONE",
    "OCEAN NETWORK EXPRESS": "ONE",
    "MSC": "MSC_EXPANSION",
    "MSC EXPANSION": "MSC_EXPANSION",
    "MSC EXPANSION PILOT": "MSC_EXPANSION",
}


# ── Partnership Manager ────────────────────────────────────────────────────

class PartnershipManager:
    """
    Manages vessel company tiers, discounts, and contract obligations.

    Usage:
        mgr = PartnershipManager()
        company = mgr.lookup("MAERSK")
        discount = mgr.get_discount("MAERSK")  # 15.0
        priority = mgr.get_priority("MAERSK")  # 1
    """

    def __init__(self, partnerships: Optional[Dict[str, VesselCompany]] = None):
        self._db: Dict[str, VesselCompany] = {}
        # Load defaults then override with provided partnerships
        self._db.update(DEFAULT_PARTNERSHIPS)
        if partnerships:
            self._db.update(partnerships)

    def resolve_company_id(self, name: str) -> str:
        """Resolve a company name/alias to a canonical company_id."""
        if not name:
            return "SPOT_MARKET"
        name_upper = name.strip().upper()
        # Direct match
        if name_upper in self._db:
            return name_upper
        # Alias match
        if name_upper in COMPANY_ALIASES:
            return COMPANY_ALIASES[name_upper]
        # Fuzzy: check if any key is a substring
        for key in self._db:
            if key in name_upper or name_upper in key:
                return key
        for alias, cid in COMPANY_ALIASES.items():
            if alias in name_upper or name_upper in alias:
                return cid
        return "SPOT_MARKET"   # Default for unknown

    def lookup(self, company_name: str) -> VesselCompany:
        """Get VesselCompany by name (resolves aliases, defaults to SPOT_MARKET)."""
        cid = self.resolve_company_id(company_name)
        return self._db.get(cid, self._db["SPOT_MARKET"])

    def get_tier(self, company_name: str) -> PartnershipTier:
        return self.lookup(company_name).tier

    def get_discount(self, company_name: str) -> float:
        return self.lookup(company_name).discount_percentage

    def get_priority(self, company_name: str) -> int:
        return self.lookup(company_name).priority

    def get_strategic_score(
        self,
        company_name: str,
        berth_code: str = "",
        is_guaranteed_berth: bool = False,
    ) -> float:
        """
        Return a strategic score 0-100 for this company-berth pairing.
        Higher = more strategically important to honor.
        """
        company = self.lookup(company_name)
        tier = company.tier

        # Base score by tier
        base = {
            PartnershipTier.VIP: 95.0,
            PartnershipTier.STRATEGIC_PROSPECT: 88.0,
            PartnershipTier.PREMIUM: 75.0,
            PartnershipTier.STANDARD: 40.0,
        }.get(tier, 40.0)

        # Contract is active bonus
        if company.is_contract_active:
            base = min(100.0, base + 5.0)

        # Guaranteed berth type bonus
        if is_guaranteed_berth and company.contract_obligations:
            if berth_code in company.contract_obligations.guaranteed_berth_types:
                base = min(100.0, base + 8.0)

        # High annual value bonus
        if company.annual_contract_value > 5_000_000:
            base = min(100.0, base + 3.0)
        elif company.annual_contract_value > 1_000_000:
            base = min(100.0, base + 1.5)

        return round(base, 2)

    def check_sla_obligation(
        self,
        company_name: str,
        planned_turnaround_hours: float,
    ) -> dict:
        """Check if a planned turnaround meets the company's SLA."""
        company = self.lookup(company_name)
        if not company.contract_obligations:
            return {"has_sla": False, "compliant": True, "sla_hours": None, "delta_hours": None}
        sla = company.contract_obligations.sla_turnaround_hours
        compliant = planned_turnaround_hours <= sla
        return {
            "has_sla": True,
            "compliant": compliant,
            "sla_hours": sla,
            "planned_hours": planned_turnaround_hours,
            "delta_hours": round(planned_turnaround_hours - sla, 1),
            "tier": company.tier.value,
        }

    def list_all(self) -> Dict[str, VesselCompany]:
        return dict(self._db)

    def upsert(self, company: VesselCompany) -> None:
        """Add or update a company in the in-memory store."""
        self._db[company.company_id] = company

    def get_all_as_table(self) -> list:
        """Return a list of dicts suitable for display in a DataFrame."""
        rows = []
        for cid, c in self._db.items():
            rows.append({
                "Company ID": cid,
                "Name": c.display_name,
                "Tier": c.tier.value,
                "Discount %": f"{c.discount_percentage:.0f}%",
                "Annual Value": f"${c.annual_contract_value:,.0f}" if c.annual_contract_value else "Variable",
                "Visits/Yr": c.visits_per_year or "Variable",
                "Contract": "✅ Active" if c.is_contract_active else ("📋 Has Contract" if c.is_contract else "❌ None"),
                "Contract Expiry": str(c.contract_expiry) if c.contract_expiry else "N/A",
                "SLA (hrs)": c.contract_obligations.sla_turnaround_hours if c.contract_obligations else "N/A",
                "Contact": f"{c.contact_person} ({c.contact_title})" if c.contact_person else "—",
                "Priority": c.priority,
            })
        return sorted(rows, key=lambda r: r["Priority"])
