"""
Calibrated Confidence Calculator — Multi-Factor Scoring.

Formula:
    Confidence = α · FeasibilityStability
               + β · PredictionCertainty
               + γ · HistoricalMatch
               + δ · CompatibilityScore

Where:
    FeasibilityStability = 1 - (constraints near violation / total constraints)
    PredictionCertainty  = f(variance, scenario stability, solver quality)
    HistoricalMatch      = cosine_similarity or default when no history
    CompatibilityScore   = vessel-berth equipment/type compatibility (0-1)
    α, β, γ, δ           = 0.25, 0.20, 0.20, 0.35

Risk levels:
    ≥ 85% → Low
    65–84% → Medium
    < 65% → High
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@dataclass
class ConfidenceResult:
    """Calibrated confidence for a decision."""
    confidence_pct: float = 0.0        # 0–100
    risk_level: str = "Medium"         # Low / Medium / High
    # Components
    feasibility_stability: float = 0.0  # 0–1
    prediction_certainty: float = 0.0   # 0–1
    historical_match: float = 0.0       # 0–1
    compatibility_score: float = 0.0    # 0–1 (NEW: equipment/type compatibility)
    # Details
    tight_constraints: List[str] = field(default_factory=list)
    explanation: str = ""
    component_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "confidence_pct": round(self.confidence_pct, 1),
            "risk_level": self.risk_level,
            "feasibility_stability": round(self.feasibility_stability, 3),
            "prediction_certainty": round(self.prediction_certainty, 3),
            "historical_match": round(self.historical_match, 3),
            "compatibility_score": round(self.compatibility_score, 3),
            "tight_constraints": self.tight_constraints,
            "explanation": self.explanation,
            "component_breakdown": self.component_breakdown,
        }


class ConfidenceCalculator:
    """
    Multi-factor calibrated confidence engine.

    Usage:
        calc = ConfidenceCalculator()
        result = calc.compute(
            feasibility_checks=checker_report.checks,
            compatibility_score=compat_score,
            solver_status=solver_status,
        )
    """

    def __init__(
        self,
        alpha: float = 0.25,   # feasibility stability weight
        beta: float = 0.20,    # prediction certainty weight
        gamma: float = 0.20,   # historical match weight
        delta: float = 0.35,   # compatibility/equipment match weight
        tight_threshold: float = 0.15,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.tight_threshold = tight_threshold

    def compute(
        self,
        feasibility_checks: Optional[list] = None,
        prediction_variance: float = 0.0,
        max_prediction_variance: float = 1.0,
        historical_features: Optional[np.ndarray] = None,
        current_features: Optional[np.ndarray] = None,
        scenario_stability: float = 1.0,
        solver_status: Optional[int] = None,
        objective_gap: float = 0.0,
        compatibility_score: float = -1.0,  # 0-100 from vessel_type_knowledge
        data_quality_gate: str = "",  # Phase 3: GREEN/YELLOW/RED from spec data
        service_uncertainty_ratio: float = 0.0,  # Phase 3: from quantile regression
    ) -> ConfidenceResult:
        """
        Compute calibrated confidence with 4-factor model.

        Args:
            feasibility_checks: List of ConstraintCheck objects
            prediction_variance: ML ensemble variance
            max_prediction_variance: For normalization
            historical_features: Historical feature matrix
            current_features: Current feature vector
            scenario_stability: Monte Carlo stability fraction
            solver_status: CP-SAT status (OPTIMAL=4, FEASIBLE=2)
            objective_gap: Solver optimality gap
            compatibility_score: Vessel-berth compatibility (0-100, -1=auto-detect)
        """
        # 1. Feasibility Stability
        fs = self._compute_feasibility_stability(feasibility_checks)

        # 2. Prediction Certainty (Phase 3: includes uncertainty ratio)
        pc = self._compute_prediction_certainty(
            prediction_variance, max_prediction_variance,
            scenario_stability, solver_status, objective_gap,
            service_uncertainty_ratio,
        )

        # 3. Historical Match
        hm = self._compute_historical_match(historical_features, current_features)

        # 4. Compatibility Score (from feasibility checks or parameter)
        cs = self._compute_compatibility_factor(
            feasibility_checks, compatibility_score,
        )

        # Phase 3: Data quality gate adjustment
        dq_multiplier = 1.0
        if data_quality_gate:
            dq_map = {"GREEN": 1.0, "YELLOW": 0.92, "RED": 0.80}
            dq_multiplier = dq_map.get(data_quality_gate.upper(), 0.90)

        # Weighted combination with 4 factors + data quality gate
        confidence = (
            self.alpha * fs +
            self.beta * pc +
            self.gamma * hm +
            self.delta * cs
        ) * dq_multiplier
        confidence_pct = round(min(max(confidence * 100, 0), 99.9), 1)

        # Risk level (updated thresholds)
        if confidence_pct >= 85:
            risk_level = "Low"
        elif confidence_pct >= 65:
            risk_level = "Medium"
        else:
            risk_level = "High"

        # Tight constraints
        tight = self._find_tight_constraints(feasibility_checks)

        # Component breakdown for UI transparency
        component_breakdown = {
            "feasibility_stability": round(fs * 100, 1),
            "prediction_certainty": round(pc * 100, 1),
            "historical_match": round(hm * 100, 1),
            "compatibility_score": round(cs * 100, 1),
            "fs_weight": self.alpha,
            "pc_weight": self.beta,
            "hm_weight": self.gamma,
            "cs_weight": self.delta,
            "fs_contribution": round(self.alpha * fs * 100, 1),
            "pc_contribution": round(self.beta * pc * 100, 1),
            "hm_contribution": round(self.gamma * hm * 100, 1),
            "cs_contribution": round(self.delta * cs * 100, 1),
        }

        # Explanation
        explanation = self._generate_explanation(
            confidence_pct, risk_level, fs, pc, hm, cs, tight
        )

        return ConfidenceResult(
            confidence_pct=confidence_pct,
            risk_level=risk_level,
            feasibility_stability=fs,
            prediction_certainty=pc,
            historical_match=hm,
            compatibility_score=cs,
            tight_constraints=tight,
            explanation=explanation,
            component_breakdown=component_breakdown,
        )

    def _compute_feasibility_stability(self, checks: Optional[list]) -> float:
        """
        Feasibility stability = 1 - (tight_constraints / total_constraints).
        A constraint is "tight" if margin < threshold.
        
        Compatible with both old ConstraintCheck (.value/.limit) and
        new ConstraintCheckResult (.margin) from data_models.py.
        """
        if not checks:
            return 0.70  # No data → moderate assumption (not magic 0.90)

        total = len(checks)
        tight = 0

        for check in checks:
            if not check.passed:
                tight += 1
            elif hasattr(check, 'margin') and isinstance(check.margin, (int, float)):
                # ConstraintCheckResult from data_models.py: margin > 0 = within limit
                # "tight" if margin is small relative to something
                # But margin is absolute (e.g. 5.0m clearance). Use heuristic:
                # treat as tight if margin < 10% of reasonable scale
                if 0 < check.margin < 2.0:  # Less than 2m/2units clearance
                    tight += 1
            elif hasattr(check, 'value') and hasattr(check, 'limit'):
                if check.limit > 0 and check.value > 0:
                    margin = 1.0 - (check.value / check.limit)
                    if 0 < margin < self.tight_threshold:
                        tight += 1

        return max(0.0, 1.0 - (tight / max(total, 1)))

    def _find_tight_constraints(self, checks: Optional[list]) -> List[str]:
        """
        Find constraints that are near their limits.
        
        Compatible with both old ConstraintCheck (.name, .detail) and
        new ConstraintCheckResult (.constraint_id, .reason) from data_models.py.
        """
        tight = []
        if not checks:
            return tight

        for check in checks:
            # Get name and detail from whichever interface is available
            name = getattr(check, 'name', None) or getattr(check, 'constraint_id', 'Unknown')
            detail = getattr(check, 'detail', None) or getattr(check, 'reason', '')

            if not check.passed:
                tight.append(f"{name}: VIOLATED — {detail}")
            elif hasattr(check, 'margin') and isinstance(check.margin, (int, float)):
                if 0 < check.margin < 2.0:
                    tight.append(
                        f"{name}: TIGHT (margin {check.margin:.1f}) — {detail}"
                    )
            elif hasattr(check, 'value') and hasattr(check, 'limit'):
                if check.limit > 0 and check.value > 0:
                    margin = 1.0 - (check.value / check.limit)
                    if 0 < margin < self.tight_threshold:
                        tight.append(
                            f"{name}: TIGHT (margin {margin*100:.0f}%) — {detail}"
                        )
        return tight

    def _compute_prediction_certainty(
        self,
        variance: float,
        max_variance: float,
        scenario_stability: float,
        solver_status: Optional[int] = None,
        objective_gap: float = 0.0,
        uncertainty_ratio: float = 0.0,
    ) -> float:
        """
        Prediction certainty = f(normalized variance, scenario stability, solver quality).
        """
        if max_variance <= 0:
            norm_var = 0.0
        else:
            norm_var = min(variance / max_variance, 1.0)

        var_certainty = 1.0 - norm_var

        # Solver quality signal
        solver_boost = 0.0
        if solver_status is not None:
            # OPTIMAL (4) = full boost, FEASIBLE (2) = partial, else = penalty
            if solver_status == 4:  # OPTIMAL
                solver_boost = 0.15
            elif solver_status == 2:  # FEASIBLE
                solver_boost = 0.05
                # Reduce by gap if available
                if objective_gap > 0:
                    solver_boost -= min(objective_gap * 0.1, 0.05)
            else:
                solver_boost = -0.2  # INFEASIBLE / MODEL_INVALID

        # Phase 3: Factor in ML uncertainty ratio from quantile regression
        uncert_penalty = min(uncertainty_ratio * 0.2, 0.15) if uncertainty_ratio > 0 else 0

        # Combine with scenario stability and solver quality
        base = 0.5 * var_certainty + 0.3 * scenario_stability
        return max(0.0, min(1.0, base + 0.2 + solver_boost - uncert_penalty))

    def _compute_historical_match(
        self,
        historical: Optional[np.ndarray],
        current: Optional[np.ndarray],
    ) -> float:
        """
        Historical match = max cosine similarity between current and historical cases.
        """
        if historical is None or current is None:
            return 0.50  # No data → neutral (not magic 0.85)

        try:
            if len(historical.shape) == 1:
                historical = historical.reshape(1, -1)
            if len(current.shape) == 1:
                current = current.reshape(1, -1)

            # Ensure same number of features
            min_cols = min(historical.shape[1], current.shape[1])
            hist = historical[:, :min_cols]
            curr = current[:, :min_cols]

            # Cosine similarity with each historical row
            curr_norm = np.linalg.norm(curr)
            if curr_norm == 0:
                return 0.5

            similarities = []
            for row in hist:
                row_norm = np.linalg.norm(row)
                if row_norm == 0:
                    continue
                sim = np.dot(row, curr.flatten()) / (row_norm * curr_norm)
                similarities.append(sim)

            if not similarities:
                return 0.5

            # Use top-5 average as match score
            top_sims = sorted(similarities, reverse=True)[:5]
            return max(0.0, min(1.0, np.mean(top_sims)))

        except Exception:
            return 0.5




    def _compute_compatibility_factor(
        self,
        checks: Optional[list],
        explicit_score: float = -1.0,
    ) -> float:
        """
        Compatibility factor from vessel-berth type/equipment matching.
        
        Sources (in priority order):
        1. Explicit compatibility_score parameter (0-100)
        2. Vessel type check 'value' from feasibility checks
        3. Default: 0.80 (moderate)
        """
        if explicit_score >= 0:
            return min(explicit_score / 100.0, 1.0)

        # Try to extract from feasibility checks
        if checks:
            for check in checks:
                if check.name == "Vessel type" and hasattr(check, 'value'):
                    if check.value is not None and check.value > 0:
                        return min(check.value / 100.0, 1.0)

        return 0.50  # No data → neutral (not magic 0.80)

    def _generate_explanation(
        self,
        confidence: float,
        risk: str,
        fs: float,
        pc: float,
        hm: float,
        cs: float,
        tight: List[str],
    ) -> str:
        """Generate human-readable confidence explanation."""
        parts = [f"Confidence: {confidence:.1f}% ({risk} risk)."]

        if fs < 0.5:
            parts.append(
                f"Feasibility concern: {len(tight)} constraint(s) tight or violated."
            )
        elif fs > 0.85:
            parts.append("All constraints satisfied with good margins.")

        if pc < 0.5:
            parts.append("High prediction uncertainty — consider reviewing.")
        elif pc > 0.8:
            parts.append("Predictions are stable across scenarios.")

        if hm < 0.5:
            parts.append("Limited historical precedent for this scenario.")
        elif hm > 0.8:
            parts.append("Strong match to historically successful decisions.")

        if cs < 0.5:
            parts.append("Low vessel-berth compatibility — equipment gaps detected.")
        elif cs > 0.8:
            parts.append("Good vessel-berth compatibility — equipment well-matched.")

        return " ".join(parts)

    def compute_delta(
        self,
        original: ConfidenceResult,
        new: ConfidenceResult,
    ) -> dict:
        """
        Compare two confidence results and return human-readable delta.

        Args:
            original: Confidence from the optimal schedule.
            new: Confidence from the overridden schedule.

        Returns:
            {
                'original': float, 'new': float, 'delta': float,
                'direction': str, 'reasons': [str],
            }
        """
        delta = new.confidence_pct - original.confidence_pct
        direction = "improved" if delta > 0 else ("degraded" if delta < 0 else "unchanged")

        reasons = []

        if abs(delta) > 2:
            reasons.append(
                f"Confidence {'dropped' if delta < 0 else 'improved'} "
                f"by {abs(delta):.1f}%"
            )

        # Compare feasibility stability
        fs_delta = new.feasibility_stability - original.feasibility_stability
        if abs(fs_delta) > 0.05:
            reasons.append(
                f"Feasibility stability {'improved' if fs_delta > 0 else 'decreased'} "
                f"({original.feasibility_stability:.0%} → {new.feasibility_stability:.0%})"
            )

        # Compare prediction certainty
        pc_delta = new.prediction_certainty - original.prediction_certainty
        if abs(pc_delta) > 0.05:
            reasons.append(
                f"Prediction certainty {'improved' if pc_delta > 0 else 'decreased'} "
                f"({original.prediction_certainty:.0%} → {new.prediction_certainty:.0%})"
            )

        # New tight constraints
        orig_tight = set(original.tight_constraints)
        new_tight = set(new.tight_constraints)
        added_tight = new_tight - orig_tight
        if added_tight:
            reasons.append(
                f"New tight constraints: {', '.join(list(added_tight)[:3])}"
            )

        # Risk level change
        if original.risk_level != new.risk_level:
            reasons.append(
                f"Risk level: {original.risk_level} → {new.risk_level}"
            )

        if not reasons:
            reasons.append("Confidence unchanged")

        return {
            "original": original.confidence_pct,
            "new": new.confidence_pct,
            "delta": delta,
            "direction": direction,
            "reasons": reasons,
        }
