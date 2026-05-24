"""
ML Models — Training Engine Layer 2
Uncertainty-aware scikit-learn models for berth decision intelligence.

Phase 2 Enhancements:
  - ServiceTimePredictor: Quantile regression (P25/P50/P75) for uncertainty bounds
  - DelayPredictor: Quantile regression for uncertainty
  - BerthSuitabilityModel: Top-3 accuracy tracking
  - DecisionRanker: Data-quality-aware weights
  - All models: Feature importance tracking
"""
from __future__ import annotations
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score


# ── Quantile Prediction Result ──────────────────────────────────────────────
@dataclass
class QuantilePrediction:
    """Prediction with uncertainty bounds."""
    point: float = 0.0        # P50 median
    lower: float = 0.0        # P25 lower bound
    upper: float = 0.0        # P75 upper bound
    confidence_width: float = 0.0  # upper - lower (narrower = more certain)

    @property
    def uncertainty_ratio(self) -> float:
        """Uncertainty as fraction of the point estimate."""
        if self.point <= 0:
            return 1.0
        return self.confidence_width / self.point


# ── Service Time Predictor ──────────────────────────────────────────────────
class ServiceTimePredictor:
    """
    Predicts expected berth occupancy hours with uncertainty bounds.
    Uses quantile regression: P25 (optimistic), P50 (median), P75 (conservative).
    """

    def __init__(self):
        # Median model (point estimate)
        self.model = GradientBoostingRegressor(
            n_estimators=100, max_depth=5, learning_rate=0.1,
            min_samples_split=5, random_state=42,
        )
        # Quantile models for uncertainty
        self.model_q25 = GradientBoostingRegressor(
            n_estimators=80, max_depth=4, learning_rate=0.1,
            loss="quantile", alpha=0.25,
            min_samples_split=5, random_state=42,
        )
        self.model_q75 = GradientBoostingRegressor(
            n_estimators=80, max_depth=4, learning_rate=0.1,
            loss="quantile", alpha=0.75,
            min_samples_split=5, random_state=42,
        )
        self.metrics: dict = {}
        self.feature_importance_: Optional[Dict[str, float]] = None

    def train(self, X: pd.DataFrame, y: pd.Series):
        # Train all three models
        self.model.fit(X, y)
        self.model_q25.fit(X, y)
        self.model_q75.fit(X, y)

        # Cross-validation on median model
        scores = cross_val_score(self.model, X, y, cv=3, scoring="neg_mean_absolute_error")
        self.metrics = {
            "mae": round(-scores.mean(), 3),
            "mae_std": round(scores.std(), 3),
            "r2": round(self.model.score(X, y), 4),
            "n_samples": len(X),
            "n_features": X.shape[1],
        }

        # Feature importance
        self.feature_importance_ = dict(
            zip(X.columns, self.model.feature_importances_)
        )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Point prediction (P50 median). Backward compatible."""
        return self.model.predict(X).clip(min=0.5)

    def predict_with_uncertainty(self, X: pd.DataFrame) -> List[QuantilePrediction]:
        """Predict with P25/P50/P75 uncertainty bounds."""
        p50 = self.model.predict(X).clip(min=0.5)
        p25 = self.model_q25.predict(X).clip(min=0.1)
        p75 = self.model_q75.predict(X).clip(min=0.5)

        results = []
        for i in range(len(p50)):
            lo = min(p25[i], p50[i])  # Ensure ordering
            hi = max(p75[i], p50[i])
            results.append(QuantilePrediction(
                point=round(float(p50[i]), 2),
                lower=round(float(lo), 2),
                upper=round(float(hi), 2),
                confidence_width=round(float(hi - lo), 2),
            ))
        return results

    def get_top_features(self, n: int = 10) -> List[tuple]:
        """Return top-n features by importance."""
        if not self.feature_importance_:
            return []
        sorted_feats = sorted(
            self.feature_importance_.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_feats[:n]

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        from sklearn.metrics import mean_absolute_error, r2_score
        pred = self.predict(X)
        quant = self.predict_with_uncertainty(X)
        avg_width = np.mean([q.confidence_width for q in quant])

        # Coverage: % of actuals falling within P25-P75 bounds
        coverage = 0
        for i, q in enumerate(quant):
            if q.lower <= y.iloc[i] <= q.upper:
                coverage += 1
        coverage_pct = coverage / max(len(y), 1) * 100

        return {
            "mae": round(mean_absolute_error(y, pred), 3),
            "r2": round(r2_score(y, pred), 4),
            "avg_uncertainty_width_h": round(avg_width, 2),
            "coverage_pct": round(coverage_pct, 1),
        }

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "model_q25": self.model_q25,
                "model_q75": self.model_q75,
                "metrics": self.metrics,
                "feature_importance": self.feature_importance_,
            }, f)

    @classmethod
    def load(cls, path: Path) -> "ServiceTimePredictor":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.model_q25 = data.get("model_q25", inst.model_q25)
        inst.model_q75 = data.get("model_q75", inst.model_q75)
        inst.metrics = data.get("metrics", {})
        inst.feature_importance_ = data.get("feature_importance")
        return inst


# ── Berth Suitability Model ────────────────────────────────────────────────
class BerthSuitabilityModel:
    """
    Predicts P(berth | vessel, conditions) — classification.
    Tracks top-3 accuracy for realistic evaluation.
    """

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=300, max_depth=None, min_samples_split=2,
            random_state=42, n_jobs=1,
        )
        self.label_encoder = LabelEncoder()
        self.metrics: dict = {}
        self.feature_importance_: Optional[Dict[str, float]] = None

    def _filter_X(self, X: pd.DataFrame) -> pd.DataFrame:
        """Drop berth-specific features to prevent data leakage."""
        from training_engine.feature_builder import BERTH_FEATURES, DERIVED_FEATURES
        cols_to_drop = [c for c in BERTH_FEATURES + DERIVED_FEATURES if c in X.columns]
        return X.drop(columns=cols_to_drop)

    def train(self, X: pd.DataFrame, y: pd.Series):
        X_filtered = self._filter_X(X)
        y_encoded = self.label_encoder.fit_transform(y)
        self.model.fit(X_filtered, y_encoded)
        scores = cross_val_score(self.model, X_filtered, y_encoded, cv=3, scoring="accuracy")
        self.metrics = {
            "accuracy": round(scores.mean(), 4),
            "accuracy_std": round(scores.std(), 4),
            "n_classes": len(self.label_encoder.classes_),
            "n_samples": len(X_filtered),
        }

        # Feature importance
        self.feature_importance_ = dict(
            zip(X_filtered.columns, self.model.feature_importances_)
        )

    def predict_proba(self, X: pd.DataFrame) -> Dict[str, float]:
        """Return {berth_code: probability} for each berth."""
        X_filtered = self._filter_X(X)
        probas = self.model.predict_proba(X_filtered)
        result = {}
        for i, cls in enumerate(self.label_encoder.classes_):
            result[str(cls)] = float(probas[0, i]) if probas.shape[0] == 1 else probas[:, i].tolist()
        return result

    def predict_top_k(self, X: pd.DataFrame, k: int = 5) -> List[tuple]:
        """Return top-k berths with probabilities."""
        X_filtered = self._filter_X(X)
        probas = self.model.predict_proba(X_filtered)[0]
        top_idx = np.argsort(probas)[::-1][:k]
        return [
            (str(self.label_encoder.classes_[i]), float(probas[i]))
            for i in top_idx
        ]

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        from sklearn.metrics import accuracy_score
        X_filtered = self._filter_X(X)
        # Filter to only labels seen during training
        known_mask = y.isin(self.label_encoder.classes_)
        if known_mask.sum() == 0:
            return {"accuracy": 0, "top3_accuracy": 0}
        X_f, y_f = X_filtered[known_mask], y[known_mask]
        y_enc = self.label_encoder.transform(y_f)

        # Top-1 accuracy
        pred = self.model.predict(X_f)
        acc = accuracy_score(y_enc, pred)

        # Top-3 accuracy: actual berth in top-3 predictions
        probas = self.model.predict_proba(X_f)
        top3_correct = 0
        for i in range(len(y_enc)):
            top3_idx = np.argsort(probas[i])[::-1][:3]
            if y_enc[i] in top3_idx:
                top3_correct += 1
        top3_acc = top3_correct / max(len(y_enc), 1)

        return {
            "accuracy": round(acc, 4),
            "top3_accuracy": round(top3_acc, 4),
        }

    def get_top_features(self, n: int = 10) -> List[tuple]:
        if not self.feature_importance_:
            return []
        sorted_feats = sorted(
            self.feature_importance_.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_feats[:n]

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "label_encoder": self.label_encoder,
                "metrics": self.metrics,
                "feature_importance": self.feature_importance_,
            }, f)

    @classmethod
    def load(cls, path: Path) -> "BerthSuitabilityModel":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.label_encoder = data["label_encoder"]
        inst.metrics = data.get("metrics", {})
        inst.feature_importance_ = data.get("feature_importance")
        return inst


# ── Delay Predictor ─────────────────────────────────────────────────────────
class DelayPredictor:
    """
    Predicts expected waiting/delay hours with uncertainty bounds.
    Uses quantile regression: P25 (optimistic), P50 (median), P75 (conservative).
    """

    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=80, max_depth=4, learning_rate=0.1,
            min_samples_split=5, random_state=42,
        )
        self.model_q25 = GradientBoostingRegressor(
            n_estimators=60, max_depth=3, learning_rate=0.1,
            loss="quantile", alpha=0.25,
            min_samples_split=5, random_state=42,
        )
        self.model_q75 = GradientBoostingRegressor(
            n_estimators=60, max_depth=3, learning_rate=0.1,
            loss="quantile", alpha=0.75,
            min_samples_split=5, random_state=42,
        )
        self.metrics: dict = {}
        self.feature_importance_: Optional[Dict[str, float]] = None

    def train(self, X: pd.DataFrame, y: pd.Series):
        self.model.fit(X, y)
        self.model_q25.fit(X, y)
        self.model_q75.fit(X, y)

        scores = cross_val_score(self.model, X, y, cv=3, scoring="neg_mean_absolute_error")
        self.metrics = {
            "mae": round(-scores.mean(), 3),
            "mae_std": round(scores.std(), 3),
            "r2": round(self.model.score(X, y), 4),
            "n_samples": len(X),
        }

        self.feature_importance_ = dict(
            zip(X.columns, self.model.feature_importances_)
        )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Point prediction. Backward compatible."""
        return self.model.predict(X).clip(min=0)

    def predict_with_uncertainty(self, X: pd.DataFrame) -> List[QuantilePrediction]:
        """Predict with P25/P50/P75 uncertainty bounds."""
        p50 = self.model.predict(X).clip(min=0)
        p25 = self.model_q25.predict(X).clip(min=0)
        p75 = self.model_q75.predict(X).clip(min=0)

        results = []
        for i in range(len(p50)):
            lo = min(p25[i], p50[i])
            hi = max(p75[i], p50[i])
            results.append(QuantilePrediction(
                point=round(float(p50[i]), 2),
                lower=round(float(lo), 2),
                upper=round(float(hi), 2),
                confidence_width=round(float(hi - lo), 2),
            ))
        return results

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        from sklearn.metrics import mean_absolute_error, r2_score
        pred = self.predict(X)
        return {
            "mae": round(mean_absolute_error(y, pred), 3),
            "r2": round(r2_score(y, pred), 4),
        }

    def get_top_features(self, n: int = 10) -> List[tuple]:
        if not self.feature_importance_:
            return []
        return sorted(
            self.feature_importance_.items(), key=lambda x: x[1], reverse=True
        )[:n]

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "model_q25": self.model_q25,
                "model_q75": self.model_q75,
                "metrics": self.metrics,
                "feature_importance": self.feature_importance_,
            }, f)

    @classmethod
    def load(cls, path: Path) -> "DelayPredictor":
        inst = cls()
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.model_q25 = data.get("model_q25", inst.model_q25)
        inst.model_q75 = data.get("model_q75", inst.model_q75)
        inst.metrics = data.get("metrics", {})
        inst.feature_importance_ = data.get("feature_importance")
        return inst


# ── Decision Ranker ─────────────────────────────────────────────────────────
@dataclass
class BerthOption:
    """A ranked berth recommendation."""
    berth_code: str
    berth_name: str
    rank: int = 0
    confidence: float = 0.0
    suitability_score: float = 0.0
    expected_wait_hours: float = 0.0
    expected_service_hours: float = 0.0
    risk_score: float = 0.0
    # Phase 2: Uncertainty bounds
    service_time_lower: float = 0.0
    service_time_upper: float = 0.0
    delay_lower: float = 0.0
    delay_upper: float = 0.0
    # Explanations
    pros: list = field(default_factory=list)
    cons: list = field(default_factory=list)
    explanation: str = ""
    # Structured explanation (new system)
    structured_explanation: Any = None   # StructuredExplanation object
    compact_reason: str = ""             # One-line deterministic reason for table


class DecisionRanker:
    """
    Combines outputs from all three ML models into a ranked list.
    Score = w_suit * suitability + w_wait * (1 - normalized_wait) + w_svc * (1 - svc_penalty)

    Phase 2: Data-quality-aware weight adjustment.
    """

    def __init__(self, w_suitability=1.0, w_wait=0.0, w_service=0.0):
        # Wait/service weights are zero because we don't have real-time port
        # occupancy data. Historical averages should NOT influence which berth
        # is selected — only shown as informational estimates.
        self.w_s = w_suitability
        self.w_w = w_wait
        self.w_v = w_service

    def rank(
        self,
        suitability_scores: Dict[str, float],
        wait_predictions: Dict[str, float],
        service_predictions: Dict[str, float],
        berth_info_map: Dict[str, dict],
        top_k: int = 3,
        # Phase 2: Optional uncertainty data
        service_uncertainty: Optional[Dict[str, QuantilePrediction]] = None,
        delay_uncertainty: Optional[Dict[str, QuantilePrediction]] = None,
    ) -> List[BerthOption]:
        """Rank berths by combined score."""
        scores = {}
        max_wait = max(wait_predictions.values(), default=1) or 1
        max_svc = max(service_predictions.values(), default=1) or 1

        for berth_code in suitability_scores:
            ml_suit = suitability_scores.get(berth_code, 0)
            bi = berth_info_map.get(berth_code, {})
            compat_score = bi.get("_compat_score", 50.0) / 100.0
            
            # ML probability is the primary signal; compat already filtered infeasible berths
            blended_suitability = ml_suit

            wait = wait_predictions.get(berth_code, max_wait)
            svc = service_predictions.get(berth_code, max_svc)

            wait_norm = 1.0 - min(wait / max_wait, 1.0)
            svc_norm = 1.0 - min(svc / (max_svc * 2), 1.0)

            # Phase 2: Penalize high-uncertainty predictions
            uncertainty_penalty = 0.0
            if service_uncertainty and berth_code in service_uncertainty:
                uq = service_uncertainty[berth_code]
                if uq.uncertainty_ratio > 0.5:
                    uncertainty_penalty = 0.05  # Mild penalty for high uncertainty

            combined = (
                self.w_s * blended_suitability + self.w_w * wait_norm + self.w_v * svc_norm
                - uncertainty_penalty
            )
            scores[berth_code] = combined

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        options = []
        for rank_idx, (bc, score) in enumerate(ranked, 1):
            bi = berth_info_map.get(bc, {})
            # Calibrated confidence
            raw_conf = score * 100
            suit_val = suitability_scores.get(bc, 0)
            if suit_val > 0.5:
                raw_conf = min(raw_conf * 1.15, 98)
            elif suit_val > 0.3:
                raw_conf = min(raw_conf * 1.05, 95)
            calibrated_conf = round(max(min(raw_conf, 98), 5), 1)

            # Uncertainty bounds
            svc_lo = svc_hi = service_predictions.get(bc, 0)
            dly_lo = dly_hi = wait_predictions.get(bc, 0)
            if service_uncertainty and bc in service_uncertainty:
                svc_lo = service_uncertainty[bc].lower
                svc_hi = service_uncertainty[bc].upper
            if delay_uncertainty and bc in delay_uncertainty:
                dly_lo = delay_uncertainty[bc].lower
                dly_hi = delay_uncertainty[bc].upper

            options.append(BerthOption(
                berth_code=bc,
                berth_name=bi.get("berth_name", bc),
                rank=rank_idx,
                confidence=calibrated_conf,
                suitability_score=round(suitability_scores.get(bc, 0) * 100, 1),
                expected_wait_hours=round(wait_predictions.get(bc, 0), 1),
                expected_service_hours=round(service_predictions.get(bc, 0), 1),
                risk_score=round(wait_predictions.get(bc, 0) / max_wait * 100, 1) if max_wait > 0 else 0,
                service_time_lower=round(svc_lo, 1),
                service_time_upper=round(svc_hi, 1),
                delay_lower=round(dly_lo, 1),
                delay_upper=round(dly_hi, 1),
            ))

        return options

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump({"w_s": self.w_s, "w_w": self.w_w, "w_v": self.w_v}, f)

    @classmethod
    def load(cls, path: Path) -> "DecisionRanker":
        with open(path, "rb") as f:
            data = pickle.load(f)
        return cls(data["w_s"], data["w_w"], data["w_v"])
