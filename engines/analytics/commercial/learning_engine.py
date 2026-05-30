"""
Commercial Learning Engine
Tracks predicted vs actual revenue, partnership SLA compliance,
and provides recommendations for weight adjustments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CommercialAssignmentRecord:
    """Record of a completed commercial assignment for learning."""
    assignment_id: str = ""
    vessel_id: str = ""
    berth_code: str = ""
    vessel_company: str = ""
    vessel_type: str = ""
    partnership_tier: str = "STANDARD"
    # Revenue
    predicted_revenue: float = 0.0
    actual_revenue: float = 0.0
    predicted_profit: float = 0.0
    actual_profit: float = 0.0
    # SLA
    planned_turnaround_hours: float = 0.0
    actual_turnaround_hours: float = 0.0
    sla_target_hours: float = 48.0
    sla_met: bool = True
    # Pricing
    discount_applied_pct: float = 0.0
    dynamic_multiplier: float = 1.0
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    decision_mode: str = "balanced"


@dataclass
class LearningInsight:
    """Generated insight from analysis of records."""
    insight_type: str = ""   # revenue_accuracy, sla_compliance, pricing_elasticity
    title: str = ""
    description: str = ""
    recommended_action: str = ""
    confidence: float = 0.0
    metric_before: float = 0.0
    metric_after: float = 0.0


class CommercialLearningEngine:
    """
    Analyzes historical commercial assignments to:
    1. Track revenue prediction accuracy
    2. Monitor SLA compliance by tier
    3. Recommend weight adjustments
    4. Detect pricing elasticity patterns
    """

    def __init__(self):
        self._records: List[CommercialAssignmentRecord] = []

    def log_assignment(self, record: CommercialAssignmentRecord) -> None:
        """Log a completed assignment for tracking."""
        self._records.append(record)

    def get_revenue_accuracy(self, min_records: int = 5) -> Optional[Dict]:
        """Compute revenue prediction accuracy statistics."""
        if len(self._records) < min_records:
            return None
        errors = []
        for r in self._records:
            if r.predicted_revenue > 0:
                err = abs(r.actual_revenue - r.predicted_revenue) / r.predicted_revenue
                errors.append(err)
        if not errors:
            return None
        avg_err = sum(errors) / len(errors)
        return {
            "mean_absolute_pct_error": round(avg_err * 100, 2),
            "num_records": len(errors),
            "accuracy_pct": round((1 - avg_err) * 100, 2),
            "is_good": avg_err < 0.10,   # <10% error = good
        }

    def get_sla_compliance_by_tier(self) -> Dict[str, Dict]:
        """SLA compliance rate per partnership tier."""
        tier_data: Dict[str, list] = {}
        for r in self._records:
            tier_data.setdefault(r.partnership_tier, []).append(r.sla_met)
        result = {}
        for tier, statuses in tier_data.items():
            compliance_rate = sum(statuses) / len(statuses) if statuses else 1.0
            result[tier] = {
                "compliance_rate_pct": round(compliance_rate * 100, 1),
                "total_calls": len(statuses),
                "met_sla": sum(statuses),
                "missed_sla": len(statuses) - sum(statuses),
            }
        return result

    def get_insights(self) -> List[LearningInsight]:
        """Generate actionable insights from recorded data."""
        insights = []
        # Revenue accuracy
        acc = self.get_revenue_accuracy()
        if acc:
            if acc["mean_absolute_pct_error"] > 15:
                insights.append(LearningInsight(
                    insight_type="revenue_accuracy",
                    title="Revenue Prediction Accuracy Below Target",
                    description=f"Mean error: {acc['mean_absolute_pct_error']:.1f}% (target: <10%)",
                    recommended_action="Review berth rate parameters and recalibrate revenue models",
                    confidence=0.85,
                    metric_before=acc["mean_absolute_pct_error"],
                    metric_after=10.0,
                ))
        # SLA compliance
        sla = self.get_sla_compliance_by_tier()
        for tier, data in sla.items():
            if tier == "VIP" and data["compliance_rate_pct"] < 95:
                insights.append(LearningInsight(
                    insight_type="sla_compliance",
                    title=f"VIP SLA Compliance Below 95%",
                    description=f"Current: {data['compliance_rate_pct']:.1f}% over {data['total_calls']} calls",
                    recommended_action="Increase strategic weight for VIP partners in decision engine",
                    confidence=0.90,
                ))
        return insights

    def get_summary_report(self) -> dict:
        """Full summary for dashboard display."""
        acc = self.get_revenue_accuracy()
        sla = self.get_sla_compliance_by_tier()
        insights = self.get_insights()
        return {
            "total_records": len(self._records),
            "revenue_accuracy": acc,
            "sla_by_tier": sla,
            "insights": [{"title": i.title, "action": i.recommended_action} for i in insights],
        }
