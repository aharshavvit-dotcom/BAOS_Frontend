"""
Structured Explanation Engine — Deterministic, Feature-Level Berth Justification.

Generates pin-point, parameter-based reasoning for every (Vessel, Berth) pair.
Replaces vague "low suitability" text with structured breakdowns like:
    ✔ LOA (180m) fits within berth limit (220m) → Safe margin: 40m
    ⚠ Beam (32m) close to limit (34m) → Tight fit
    ❌ Draft (12.5m) exceeds berth depth (10.0m) → Not feasible

Categories:
    1. PHYSICAL FIT     — LOA, Draft, Beam, DWT
    2. OPERATIONAL       — Cargo compatibility, vessel type, equipment, storage
    3. PERFORMANCE       — Waiting time, service time
    4. COMMERCIAL IMPACT — Cost, SLA risk
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── Status Classification ────────────────────────────────────────────────────

class AssessmentStatus(str, Enum):
    """Status of a single parameter check."""
    PASS = "pass"       # ✔ Comfortable fit
    OK = "ok"           # ✔ Acceptable
    TIGHT = "tight"     # ⚠ Close to limit
    FAIL = "fail"       # ❌ Violation
    INFO = "info"       # ℹ Informational only
    UNKNOWN = "unknown" # ? Missing data


STATUS_ICONS = {
    AssessmentStatus.PASS: "✔",
    AssessmentStatus.OK: "✔",
    AssessmentStatus.TIGHT: "⚠",
    AssessmentStatus.FAIL: "❌",
    AssessmentStatus.INFO: "ℹ",
    AssessmentStatus.UNKNOWN: "?",
}

STATUS_CSS_CLASS = {
    AssessmentStatus.PASS: "exp-pass",
    AssessmentStatus.OK: "exp-ok",
    AssessmentStatus.TIGHT: "exp-tight",
    AssessmentStatus.FAIL: "exp-fail",
    AssessmentStatus.INFO: "exp-info",
    AssessmentStatus.UNKNOWN: "exp-unknown",
}


class ExplanationCategory(str, Enum):
    PHYSICAL = "Physical Fit"
    OPERATIONAL = "Operational"
    PERFORMANCE = "Performance"
    COMMERCIAL = "Commercial Impact"


CATEGORY_EMOJI = {
    ExplanationCategory.PHYSICAL: "🔧",
    ExplanationCategory.OPERATIONAL: "⚙️",
    ExplanationCategory.PERFORMANCE: "📊",
    ExplanationCategory.COMMERCIAL: "💰",
}


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class ParameterAssessment:
    """Result of evaluating one parameter (e.g. LOA, Draft, Cargo type)."""
    category: ExplanationCategory
    parameter_name: str
    vessel_value: Any = None
    berth_limit: Any = None
    slack: Optional[float] = None  # limit - actual (positive = good)
    slack_pct: Optional[float] = None  # slack as % of limit
    status: AssessmentStatus = AssessmentStatus.UNKNOWN
    detail_text: str = ""   # Full text for expanded view
    compact_text: str = ""  # Short text for table column
    is_hard_constraint: bool = True

    @property
    def icon(self) -> str:
        return STATUS_ICONS.get(self.status, "?")

    @property
    def css_class(self) -> str:
        return STATUS_CSS_CLASS.get(self.status, "exp-unknown")


@dataclass
class CategoryBreakdown:
    """Group of assessments for one category."""
    category: ExplanationCategory
    assessments: List[ParameterAssessment] = field(default_factory=list)

    @property
    def emoji(self) -> str:
        return CATEGORY_EMOJI.get(self.category, "")

    @property
    def pass_count(self) -> int:
        return sum(1 for a in self.assessments if a.status in (AssessmentStatus.PASS, AssessmentStatus.OK))

    @property
    def warn_count(self) -> int:
        return sum(1 for a in self.assessments if a.status == AssessmentStatus.TIGHT)

    @property
    def fail_count(self) -> int:
        return sum(1 for a in self.assessments if a.status == AssessmentStatus.FAIL)

    @property
    def summary_line(self) -> str:
        """One-line summary like '3 pass, 1 tight, 0 fail'."""
        parts = []
        if self.pass_count:
            parts.append(f"{self.pass_count} pass")
        if self.warn_count:
            parts.append(f"{self.warn_count} tight")
        if self.fail_count:
            parts.append(f"{self.fail_count} fail")
        return ", ".join(parts) if parts else "No checks"


@dataclass
class StructuredExplanation:
    """Complete structured explanation for one vessel-berth pair."""
    vessel_name: str = ""
    berth_code: str = ""
    berth_name: str = ""

    # 4 category breakdowns
    physical: CategoryBreakdown = field(
        default_factory=lambda: CategoryBreakdown(ExplanationCategory.PHYSICAL)
    )
    operational: CategoryBreakdown = field(
        default_factory=lambda: CategoryBreakdown(ExplanationCategory.OPERATIONAL)
    )
    performance: CategoryBreakdown = field(
        default_factory=lambda: CategoryBreakdown(ExplanationCategory.PERFORMANCE)
    )
    commercial: CategoryBreakdown = field(
        default_factory=lambda: CategoryBreakdown(ExplanationCategory.COMMERCIAL)
    )

    # Summary texts
    final_summary: str = ""
    compact_summary: str = ""
    trade_off_sentence: str = ""

    # Feasibility
    is_feasible: bool = True
    hard_violations: List[str] = field(default_factory=list)

    @property
    def all_categories(self) -> List[CategoryBreakdown]:
        return [self.physical, self.operational, self.performance, self.commercial]

    @property
    def all_assessments(self) -> List[ParameterAssessment]:
        items = []
        for cat in self.all_categories:
            items.extend(cat.assessments)
        return items

    @property
    def total_pass(self) -> int:
        return sum(c.pass_count for c in self.all_categories)

    @property
    def total_warn(self) -> int:
        return sum(c.warn_count for c in self.all_categories)

    @property
    def total_fail(self) -> int:
        return sum(c.fail_count for c in self.all_categories)

    def get_pros(self) -> List[str]:
        """Extract ✔ items as pros list (for backward compat)."""
        return [
            f"{a.icon} {a.detail_text}"
            for a in self.all_assessments
            if a.status in (AssessmentStatus.PASS, AssessmentStatus.OK)
        ]

    def get_cons(self) -> List[str]:
        """Extract ⚠/❌ items as cons list (for backward compat)."""
        return [
            f"{a.icon} {a.detail_text}"
            for a in self.all_assessments
            if a.status in (AssessmentStatus.TIGHT, AssessmentStatus.FAIL)
        ]


# ── Slack Classification Helpers ──────────────────────────────────────────────

def _classify_numeric_slack(
    actual: float,
    limit: float,
    tight_pct: float = 0.05,
    ok_pct: float = 0.20,
) -> Tuple[float, float, AssessmentStatus]:
    """
    Classify a numeric constraint by slack.

    Returns (slack, slack_pct, status).
    Thresholds:
        slack_pct > ok_pct  → PASS  (strong fit)
        slack_pct > tight_pct → OK  (acceptable)
        slack_pct > 0        → TIGHT (close to limit)
        slack_pct <= 0       → FAIL  (violation)
    """
    if limit <= 0:
        return 0.0, 0.0, AssessmentStatus.UNKNOWN

    slack = limit - actual
    slack_pct = slack / limit

    if slack < 0:
        return slack, slack_pct, AssessmentStatus.FAIL
    elif slack_pct <= tight_pct:
        return slack, slack_pct, AssessmentStatus.TIGHT
    elif slack_pct <= ok_pct:
        return slack, slack_pct, AssessmentStatus.OK
    else:
        return slack, slack_pct, AssessmentStatus.PASS


def _classify_time(hours: float, low_thresh: float, high_thresh: float) -> AssessmentStatus:
    """Classify a time metric. Lower is better."""
    if hours <= low_thresh:
        return AssessmentStatus.PASS
    elif hours <= high_thresh:
        return AssessmentStatus.OK
    else:
        return AssessmentStatus.TIGHT


# ── Main Engine ───────────────────────────────────────────────────────────────

class StructuredExplanationEngine:
    """
    Generates deterministic, feature-level explanations for (Vessel, Berth) pairs.

    Usage:
        engine = StructuredExplanationEngine()
        explanation = engine.explain(
            vessel={"loa": 180, "draft": 9.5, "beam": 32, ...},
            berth_info={"max_loa_m": 220, "depth_m": 12, ...},
            wait_hours=22.4,
            service_hours=14.6,
        )
        print(explanation.compact_summary)
        print(explanation.final_summary)
    """

    def explain(
        self,
        vessel: dict,
        berth_info: dict,
        wait_hours: float = 0.0,
        service_hours: float = 0.0,
        cost_breakdown: Optional[dict] = None,
        sla_max_wait_hours: float = 24.0,
        feasibility_result=None,  # Optional FeasibilityResult from constraint lib
        wait_lower: float = 0.0,
        wait_upper: float = 0.0,
        service_lower: float = 0.0,
        service_upper: float = 0.0,
    ) -> StructuredExplanation:
        """
        Generate structured explanation for a vessel-berth pair.

        Args:
            vessel: Dict with loa, draft, beam, dwt, cargo_type, vessel_type, cargo_tons
            berth_info: Dict with max_loa_m, max_draft_m, depth_m, max_beam_m,
                        allowed_vessel_types, equipment, allowed_cargo_types, etc.
            wait_hours: Predicted/historical waiting time
            service_hours: Predicted/historical service time
            cost_breakdown: Optional dict with cost fields
            sla_max_wait_hours: SLA wait limit
            feasibility_result: Optional FeasibilityResult from ConstraintLibrary
            wait_lower/wait_upper: Uncertainty bounds for wait
            service_lower/service_upper: Uncertainty bounds for service
        """
        expl = StructuredExplanation(
            vessel_name=vessel.get("name", vessel.get("vessel_id", "Vessel")),
            berth_code=berth_info.get("berth_code", ""),
            berth_name=berth_info.get("berth_name", berth_info.get("berth_code", "")),
        )

        # 1. Physical Fit
        self._assess_physical(expl, vessel, berth_info)

        # 2. Operational
        self._assess_operational(expl, vessel, berth_info)

        # 3. Performance
        self._assess_performance(
            expl, wait_hours, service_hours,
            wait_lower, wait_upper, service_lower, service_upper,
        )

        # 4. Commercial
        self._assess_commercial(expl, wait_hours, cost_breakdown, sla_max_wait_hours)

        # Feasibility determination
        expl.hard_violations = [
            a.detail_text for a in expl.all_assessments
            if a.status == AssessmentStatus.FAIL and a.is_hard_constraint
        ]
        expl.is_feasible = len(expl.hard_violations) == 0

        # Generate summaries
        expl.compact_summary = self._build_compact_summary(expl)
        expl.final_summary = self._build_final_summary(expl, wait_hours)
        expl.trade_off_sentence = self._build_trade_off(expl, wait_hours, service_hours)

        return expl

    # ── Physical Fit ──────────────────────────────────────────────────────

    def _assess_physical(
        self,
        expl: StructuredExplanation,
        vessel: dict,
        berth_info: dict,
    ):
        cat = expl.physical

        vessel_loa = float(vessel.get("loa", 0))
        vessel_draft = float(vessel.get("draft", vessel.get("adraft", 0)))
        vessel_beam = float(vessel.get("beam", 0))
        vessel_dwt = float(vessel.get("dwt", 0))

        max_loa = float(berth_info.get("max_loa_m", 0))
        max_draft = float(berth_info.get("max_draft_m", 0))
        depth = float(berth_info.get("depth_m", 0))
        max_beam = float(berth_info.get("max_beam_m", 0))

        # LOA
        if vessel_loa > 0 and max_loa > 0:
            slack, slack_pct, status = _classify_numeric_slack(vessel_loa, max_loa)
            if status == AssessmentStatus.FAIL:
                detail = f"LOA ({vessel_loa:.0f}m) exceeds berth limit ({max_loa:.0f}m) → Not feasible (excess: {abs(slack):.0f}m)"
                compact = f"LOA exceeds by {abs(slack):.0f}m"
            elif status == AssessmentStatus.TIGHT:
                detail = f"LOA ({vessel_loa:.0f}m) close to berth limit ({max_loa:.0f}m) → Tight fit (margin: {slack:.0f}m)"
                compact = f"Tight LOA fit ({slack:.0f}m margin)"
            else:
                detail = f"LOA ({vessel_loa:.0f}m) fits within berth limit ({max_loa:.0f}m) → Safe margin: {slack:.0f}m"
                compact = f"Good LOA fit"
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.PHYSICAL,
                parameter_name="LOA",
                vessel_value=vessel_loa,
                berth_limit=max_loa,
                slack=slack, slack_pct=slack_pct,
                status=status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=True,
            ))

        # Draft / Depth clearance
        if vessel_draft > 0 and (max_draft > 0 or depth > 0):
            effective_limit = depth if depth > 0 else max_draft
            slack, slack_pct, status = _classify_numeric_slack(vessel_draft, effective_limit)
            clearance = effective_limit - vessel_draft

            if status == AssessmentStatus.FAIL:
                detail = f"Draft ({vessel_draft:.1f}m) exceeds berth depth ({effective_limit:.1f}m) → Not feasible"
                compact = f"Draft exceeds depth"
            elif status == AssessmentStatus.TIGHT:
                detail = f"Draft ({vessel_draft:.1f}m) within depth ({effective_limit:.1f}m) → Tight clearance: {clearance:.1f}m"
                compact = f"Tight draft ({clearance:.1f}m clearance)"
            else:
                detail = f"Draft ({vessel_draft:.1f}m) within depth ({effective_limit:.1f}m) → Clearance OK: {clearance:.1f}m"
                compact = f"Good draft clearance"

            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.PHYSICAL,
                parameter_name="Draft",
                vessel_value=vessel_draft,
                berth_limit=effective_limit,
                slack=slack, slack_pct=slack_pct,
                status=status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=True,
            ))

        # Beam
        if vessel_beam > 0 and max_beam > 0 and max_beam < 999:
            slack, slack_pct, status = _classify_numeric_slack(vessel_beam, max_beam)
            if status == AssessmentStatus.FAIL:
                detail = f"Beam ({vessel_beam:.0f}m) exceeds berth limit ({max_beam:.0f}m) → Not feasible"
                compact = f"Beam exceeds limit"
            elif status == AssessmentStatus.TIGHT:
                detail = f"Beam ({vessel_beam:.0f}m) close to limit ({max_beam:.0f}m) → Tight fit (margin: {slack:.0f}m)"
                compact = f"Tight beam fit"
            else:
                detail = f"Beam ({vessel_beam:.0f}m) fits within limit ({max_beam:.0f}m) → Margin: {slack:.0f}m"
                compact = f"Good beam fit"
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.PHYSICAL,
                parameter_name="Beam",
                vessel_value=vessel_beam,
                berth_limit=max_beam,
                slack=slack, slack_pct=slack_pct,
                status=status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=True,
            ))

        # DWT (if berth has a limit)
        max_dwt = float(berth_info.get("max_dwt", 0))
        if vessel_dwt > 0 and max_dwt > 0:
            slack, slack_pct, status = _classify_numeric_slack(vessel_dwt, max_dwt)
            if status == AssessmentStatus.FAIL:
                detail = f"DWT ({vessel_dwt:,.0f}t) exceeds berth limit ({max_dwt:,.0f}t) → Not feasible"
                compact = f"DWT exceeds limit"
            else:
                detail = f"DWT ({vessel_dwt:,.0f}t) within limit ({max_dwt:,.0f}t)"
                compact = f"DWT OK"
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.PHYSICAL,
                parameter_name="DWT",
                vessel_value=vessel_dwt,
                berth_limit=max_dwt,
                slack=slack, slack_pct=slack_pct,
                status=status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=True,
            ))

    # ── Operational ────────────────────────────────────────────────────────

    def _assess_operational(
        self,
        expl: StructuredExplanation,
        vessel: dict,
        berth_info: dict,
    ):
        cat = expl.operational
        cargo_type = vessel.get("cargo_type", "")
        vessel_type = vessel.get("vessel_type", "")
        cargo_tons = float(vessel.get("cargo_tons", 0))

        # Cargo compatibility
        allowed_cargo = berth_info.get("allowed_cargo_types", [])
        cargo_cats = berth_info.get("cargo_categories", [])
        supported_commodities = berth_info.get("supported_commodities", [])
        equipment = berth_info.get("equipment", berth_info.get("equipment_types", []))

        if cargo_type:
            # Check match against allowed cargo types / categories
            cargo_lower = cargo_type.lower().strip()
            exact_match = any(cargo_lower == c.lower().strip() for c in allowed_cargo) if allowed_cargo else False
            cat_match = any(cargo_lower in c.lower() or c.lower() in cargo_lower for c in cargo_cats) if cargo_cats else False
            commodity_match = any(cargo_lower in c.lower() or c.lower() in cargo_lower for c in supported_commodities) if supported_commodities else False

            if exact_match or cat_match or commodity_match:
                detail = f"Cargo type ({cargo_type}) supported by berth"
                if equipment:
                    detail += f" (equipment: {', '.join(equipment[:3])})"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.OPERATIONAL,
                    parameter_name="Cargo Compatibility",
                    vessel_value=cargo_type,
                    berth_limit=", ".join(allowed_cargo[:5]) if allowed_cargo else ", ".join(cargo_cats[:5]),
                    status=AssessmentStatus.PASS,
                    detail_text=detail,
                    compact_text="Cargo compatible",
                    is_hard_constraint=False,
                ))
            elif allowed_cargo or cargo_cats:
                avail = allowed_cargo if allowed_cargo else list(cargo_cats)
                detail = f"Cargo type ({cargo_type}) not in berth's typical types ({', '.join(avail[:4])})"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.OPERATIONAL,
                    parameter_name="Cargo Compatibility",
                    vessel_value=cargo_type,
                    berth_limit=", ".join(avail[:4]),
                    status=AssessmentStatus.TIGHT,
                    detail_text=detail,
                    compact_text="Cargo type atypical",
                    is_hard_constraint=False,
                ))
            else:
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.OPERATIONAL,
                    parameter_name="Cargo Compatibility",
                    vessel_value=cargo_type,
                    status=AssessmentStatus.INFO,
                    detail_text=f"No cargo type restriction data available for this berth",
                    compact_text="No cargo data",
                    is_hard_constraint=False,
                ))

        # Vessel type
        allowed_types = berth_info.get("allowed_vessel_types", [])
        if vessel_type and allowed_types:
            vt_lower = vessel_type.lower().strip()
            type_match = any(
                vt_lower in t.lower() or t.lower() in vt_lower
                for t in allowed_types
            )
            if type_match:
                detail = f"Vessel type ({vessel_type}) allowed at berth"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.OPERATIONAL,
                    parameter_name="Vessel Type",
                    vessel_value=vessel_type,
                    berth_limit=", ".join(allowed_types[:4]),
                    status=AssessmentStatus.PASS,
                    detail_text=detail,
                    compact_text="Vessel type OK",
                    is_hard_constraint=False,
                ))
            else:
                detail = f"Vessel type ({vessel_type}) not in allowed types ({', '.join(allowed_types[:4])})"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.OPERATIONAL,
                    parameter_name="Vessel Type",
                    vessel_value=vessel_type,
                    berth_limit=", ".join(allowed_types[:4]),
                    status=AssessmentStatus.TIGHT,
                    detail_text=detail,
                    compact_text="Vessel type atypical",
                    is_hard_constraint=False,
                ))

        # Equipment availability
        if equipment:
            detail = f"Berth equipment available: {', '.join(equipment[:4])}"
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.OPERATIONAL,
                parameter_name="Equipment",
                vessel_value="Required",
                berth_limit=", ".join(equipment[:4]),
                status=AssessmentStatus.PASS,
                detail_text=detail,
                compact_text="Equipment available",
                is_hard_constraint=False,
            ))

        # Shore storage capacity
        shore_cap = float(berth_info.get("shore_storage_capacity_tons", 0))
        if cargo_tons > 0 and shore_cap > 0:
            slack, slack_pct, status = _classify_numeric_slack(cargo_tons, shore_cap)
            if status == AssessmentStatus.FAIL:
                detail = f"Cargo ({cargo_tons:,.0f}t) exceeds shore capacity ({shore_cap:,.0f}t)"
                compact = "Shore capacity insufficient"
            else:
                detail = f"Shore capacity sufficient ({shore_cap:,.0f}t > {cargo_tons:,.0f}t cargo)"
                compact = "Shore capacity OK"
                status = AssessmentStatus.PASS
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.OPERATIONAL,
                parameter_name="Shore Storage",
                vessel_value=cargo_tons,
                berth_limit=shore_cap,
                slack=slack,
                status=status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=False,
            ))

        # Working hours
        allow_24x7 = berth_info.get("allow_24x7", True)
        if allow_24x7:
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.OPERATIONAL,
                parameter_name="Working Hours",
                status=AssessmentStatus.PASS,
                detail_text="Berth operates 24x7 — no time restrictions",
                compact_text="24x7 operations",
                is_hard_constraint=False,
            ))
        else:
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.OPERATIONAL,
                parameter_name="Working Hours",
                status=AssessmentStatus.TIGHT,
                detail_text="Berth has restricted working hours — may delay operations",
                compact_text="Limited working hours",
                is_hard_constraint=False,
            ))

        # Tidal restriction
        if berth_info.get("tidal_restricted"):
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.OPERATIONAL,
                parameter_name="Tidal Restriction",
                status=AssessmentStatus.TIGHT,
                detail_text="Berth is tidal restricted — arrival/departure timing constrained",
                compact_text="Tidal restricted",
                is_hard_constraint=False,
            ))

    # ── Performance ────────────────────────────────────────────────────────

    def _assess_performance(
        self,
        expl: StructuredExplanation,
        wait_hours: float,
        service_hours: float,
        wait_lower: float = 0.0,
        wait_upper: float = 0.0,
        service_lower: float = 0.0,
        service_upper: float = 0.0,
    ):
        cat = expl.performance

        # Waiting time
        if wait_hours >= 0:
            wait_status = _classify_time(wait_hours, 2.0, 8.0)
            uncert = ""
            if wait_lower > 0 or wait_upper > 0:
                uncert = f" (range: {wait_lower:.1f}-{wait_upper:.1f}h)"

            if wait_status == AssessmentStatus.PASS:
                detail = f"Short predicted wait ({wait_hours:.1f}h){uncert}"
                compact = f"Low wait ({wait_hours:.1f}h)"
            elif wait_status == AssessmentStatus.OK:
                detail = f"Acceptable predicted wait ({wait_hours:.1f}h){uncert}"
                compact = f"Moderate wait ({wait_hours:.1f}h)"
            else:
                detail = f"High predicted wait ({wait_hours:.1f}h){uncert} → Congestion likely"
                compact = f"High wait ({wait_hours:.1f}h)"

            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.PERFORMANCE,
                parameter_name="Waiting Time",
                vessel_value=wait_hours,
                status=wait_status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=False,
            ))

        # Service time
        if service_hours > 0:
            svc_status = _classify_time(service_hours, 12.0, 36.0)
            uncert = ""
            if service_lower > 0 or service_upper > 0:
                uncert = f" (range: {service_lower:.0f}-{service_upper:.0f}h)"

            if svc_status == AssessmentStatus.PASS:
                detail = f"Fast service time ({service_hours:.1f}h){uncert}"
                compact = f"Fast service ({service_hours:.0f}h)"
            elif svc_status == AssessmentStatus.OK:
                detail = f"Standard service time ({service_hours:.1f}h){uncert}"
                compact = f"Normal service ({service_hours:.0f}h)"
            else:
                detail = f"Long service time ({service_hours:.1f}h){uncert}"
                compact = f"Long service ({service_hours:.0f}h)"

            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.PERFORMANCE,
                parameter_name="Service Time",
                vessel_value=service_hours,
                status=svc_status,
                detail_text=detail,
                compact_text=compact,
                is_hard_constraint=False,
            ))

    # ── Commercial Impact ──────────────────────────────────────────────────

    def _assess_commercial(
        self,
        expl: StructuredExplanation,
        wait_hours: float,
        cost_breakdown: Optional[dict],
        sla_max_wait_hours: float,
    ):
        cat = expl.commercial

        # SLA risk
        if sla_max_wait_hours > 0:
            sla_slack = sla_max_wait_hours - wait_hours
            if sla_slack < 0:
                detail = f"SLA breach: wait ({wait_hours:.1f}h) exceeds limit ({sla_max_wait_hours:.0f}h) by {abs(sla_slack):.1f}h"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.COMMERCIAL,
                    parameter_name="SLA Risk",
                    vessel_value=wait_hours,
                    berth_limit=sla_max_wait_hours,
                    slack=sla_slack,
                    status=AssessmentStatus.FAIL,
                    detail_text=detail,
                    compact_text="SLA breach risk",
                    is_hard_constraint=False,
                ))
            elif sla_slack < 4:
                detail = f"SLA margin is tight: {sla_slack:.1f}h headroom remaining"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.COMMERCIAL,
                    parameter_name="SLA Risk",
                    vessel_value=wait_hours,
                    berth_limit=sla_max_wait_hours,
                    slack=sla_slack,
                    status=AssessmentStatus.TIGHT,
                    detail_text=detail,
                    compact_text="SLA tight",
                    is_hard_constraint=False,
                ))
            else:
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.COMMERCIAL,
                    parameter_name="SLA Risk",
                    status=AssessmentStatus.PASS,
                    detail_text="No SLA risk — wait well within limits",
                    compact_text="No SLA risk",
                    is_hard_constraint=False,
                ))

        # Cost impact from waiting
        if wait_hours > 6:
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.COMMERCIAL,
                parameter_name="Waiting Cost",
                status=AssessmentStatus.TIGHT,
                detail_text=f"Higher waiting cost due to {wait_hours:.1f}h predicted wait",
                compact_text="Higher wait cost",
                is_hard_constraint=False,
            ))
        elif wait_hours <= 2:
            cat.assessments.append(ParameterAssessment(
                category=ExplanationCategory.COMMERCIAL,
                parameter_name="Waiting Cost",
                status=AssessmentStatus.PASS,
                detail_text=f"Low waiting cost — short wait ({wait_hours:.1f}h)",
                compact_text="Low wait cost",
                is_hard_constraint=False,
            ))

        # Detailed cost breakdown if available
        if cost_breakdown:
            total = cost_breakdown.get("total_cost", 0)
            if total > 0:
                # FIX (Phase 7.1): Use configurable currency symbol instead of hardcoded $.
                try:
                    from backend.config.settings import settings
                    sym = settings.CURRENCY_SYMBOL
                except Exception:
                    sym = "₹"
                cat.assessments.append(ParameterAssessment(
                    category=ExplanationCategory.COMMERCIAL,
                    parameter_name="Estimated Cost",
                    vessel_value=total,
                    status=AssessmentStatus.INFO,
                    detail_text=f"Estimated total cost: {sym}{total:,.0f}",
                    compact_text=f"Cost: {sym}{total:,.0f}",
                    is_hard_constraint=False,
                ))

    # ── Summary Builders ──────────────────────────────────────────────────

    def _build_compact_summary(self, expl: StructuredExplanation) -> str:
        """
        Build short summary for table column.
        Format: "Good LOA/draft fit + High wait (22h) + Cargo compatible"
        Picks the most notable items: 1 physical + 1 performance + 1 operational.
        """
        if not expl.is_feasible:
            violations = " + ".join(expl.hard_violations[:2])
            return f"❌ {violations}"

        parts = []

        # Pick most notable physical
        phys_items = expl.physical.assessments
        if phys_items:
            fails = [a for a in phys_items if a.status == AssessmentStatus.FAIL]
            tights = [a for a in phys_items if a.status == AssessmentStatus.TIGHT]
            if fails:
                parts.append(fails[0].compact_text)
            elif tights:
                parts.append(tights[0].compact_text)
            else:
                # Summarize as combined
                names = [a.parameter_name for a in phys_items
                         if a.status in (AssessmentStatus.PASS, AssessmentStatus.OK)]
                if names:
                    parts.append(f"Good {'/'.join(names[:2]).lower()} fit")

        # Pick performance note
        perf_items = expl.performance.assessments
        for a in perf_items:
            if a.parameter_name == "Waiting Time":
                parts.append(a.compact_text)
                break

        # Pick operational note
        op_items = expl.operational.assessments
        cargo_item = next((a for a in op_items if a.parameter_name == "Cargo Compatibility"), None)
        if cargo_item:
            parts.append(cargo_item.compact_text)

        return " + ".join(parts[:3]) if parts else "Evaluated"

    def _build_final_summary(self, expl: StructuredExplanation, wait_hours: float) -> str:
        """
        Build narrative final summary.
        Example: "Physically suitable but operationally suboptimal due to high congestion..."
        """
        if not expl.is_feasible:
            reasons = "; ".join(expl.hard_violations[:3])
            return f"Not feasible — {reasons}"

        physical_good = expl.physical.fail_count == 0 and expl.physical.warn_count == 0
        physical_tight = expl.physical.warn_count > 0
        op_good = expl.operational.fail_count == 0 and expl.operational.warn_count == 0
        perf_good = all(
            a.status in (AssessmentStatus.PASS, AssessmentStatus.OK)
            for a in expl.performance.assessments
        ) if expl.performance.assessments else True

        parts = []

        # Physical
        if physical_good:
            phys_details = []
            for a in expl.physical.assessments:
                if a.slack is not None and a.slack > 0:
                    phys_details.append(f"{a.parameter_name} clearance +{a.slack:.0f}{'m' if a.parameter_name != 'DWT' else 't'}")
            if phys_details:
                parts.append(f"Physically suitable ({', '.join(phys_details[:2])})")
            else:
                parts.append("Physically suitable")
        elif physical_tight:
            tight_names = [a.parameter_name.lower() for a in expl.physical.assessments
                           if a.status == AssessmentStatus.TIGHT]
            parts.append(f"Physical fit is tight on {', '.join(tight_names)}")
        else:
            parts.append("Physical constraints violated")

        # Operational
        if not op_good:
            op_issues = [a.compact_text.lower() for a in expl.operational.assessments
                         if a.status in (AssessmentStatus.TIGHT, AssessmentStatus.FAIL)]
            if op_issues:
                parts.append(f"operational concerns: {', '.join(op_issues[:2])}")

        # Performance
        if not perf_good:
            wait_item = next(
                (a for a in expl.performance.assessments if a.parameter_name == "Waiting Time"),
                None,
            )
            if wait_item and wait_item.status == AssessmentStatus.TIGHT:
                parts.append(f"high predicted wait ({wait_hours:.1f}h) reduces efficiency")
            svc_item = next(
                (a for a in expl.performance.assessments if a.parameter_name == "Service Time"),
                None,
            )
            if svc_item and svc_item.status == AssessmentStatus.TIGHT:
                parts.append(f"long service time ({svc_item.vessel_value:.0f}h)")

        # Commercial
        comm_issues = [a for a in expl.commercial.assessments
                       if a.status in (AssessmentStatus.TIGHT, AssessmentStatus.FAIL)]
        if comm_issues:
            parts.append("; ".join(i.compact_text.lower() for i in comm_issues[:2]))

        # Join with connectors
        if len(parts) == 1:
            return parts[0]

        # Use "but" connector if physical is good but performance/op is not
        if physical_good and (not perf_good or not op_good):
            return f"{parts[0]}, but {' — '.join(parts[1:])}"

        return " — ".join(parts)

    def _build_trade_off(
        self,
        expl: StructuredExplanation,
        wait_hours: float,
        service_hours: float,
    ) -> str:
        """Build trade-off sentence for advanced UI."""
        if not expl.is_feasible:
            return ""

        goods = []
        bads = []

        for a in expl.all_assessments:
            if a.status in (AssessmentStatus.PASS, AssessmentStatus.OK):
                goods.append(a.compact_text.lower())
            elif a.status in (AssessmentStatus.TIGHT, AssessmentStatus.FAIL):
                bads.append(a.compact_text.lower())

        if goods and bads:
            return (
                f"Strengths: {', '.join(goods[:3])}. "
                f"Trade-offs: {', '.join(bads[:3])}"
            )
        elif goods:
            return f"Strong option: {', '.join(goods[:3])}"
        elif bads:
            return f"Concerns: {', '.join(bads[:3])}"
        return ""


# ── Comparison Helper ─────────────────────────────────────────────────────────

def build_comparison_insight(
    option_a: StructuredExplanation,
    option_b: StructuredExplanation,
    wait_a: float,
    wait_b: float,
    service_a: float,
    service_b: float,
) -> str:
    """
    Generate comparison insight between two berth options.
    Example: "Compared to Berth JD3, this option has 20% lower wait but tighter draft clearance"
    """
    parts = []

    # Wait comparison
    if abs(wait_a - wait_b) > 0.5:
        pct = abs(wait_a - wait_b) / max(wait_b, 0.1) * 100
        if wait_a < wait_b:
            parts.append(f"{pct:.0f}% lower wait")
        else:
            parts.append(f"{pct:.0f}% higher wait")

    # Service comparison
    if abs(service_a - service_b) > 1:
        if service_a < service_b:
            parts.append(f"faster service ({service_a:.0f}h vs {service_b:.0f}h)")
        else:
            parts.append(f"slower service ({service_a:.0f}h vs {service_b:.0f}h)")

    # Physical fit comparison
    draft_a = next((a for a in option_a.physical.assessments if a.parameter_name == "Draft"), None)
    draft_b = next((a for a in option_b.physical.assessments if a.parameter_name == "Draft"), None)
    if draft_a and draft_b and draft_a.slack is not None and draft_b.slack is not None:
        if abs(draft_a.slack - draft_b.slack) > 0.5:
            if draft_a.slack > draft_b.slack:
                parts.append("better draft clearance")
            else:
                parts.append("tighter draft clearance")

    if parts:
        name_b = option_b.berth_name or option_b.berth_code
        return f"Compared to {name_b}: {' but '.join(parts[:3])}"
    return ""
