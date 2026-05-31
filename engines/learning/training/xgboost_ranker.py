"""
XGBoost Berth Ranker — Training Engine Layer 2.5

Learns optimal berth ranking from historical assignment decisions.
Uses XGBClassifier for multiclass classification (predict best berth)
with pattern-derived and commercial features on top of the 22 base features.

Gracefully degrades to a lightweight Random Forest if xgboost is not
installed, so the rest of the system never breaks.
"""
from __future__ import annotations

import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger(__name__)

from backend.config.settings import settings
from engines.learning.training.ml_models import verify_feature_hash, write_feature_hash

# Try to import XGBoost; fall back to Random Forest if unavailable
try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
    logger.info("XGBoost available — using XGBClassifier for ranking")
except ImportError:
    _HAS_XGB = False
    logger.info("XGBoost not installed — falling back to RandomForest ranker")


class XGBoostBerthRanker:
    """
    Multiclass classifier that predicts P(berth | vessel_features).

    Features expected:
      - 22 base features from feature_builder
      - specialization_score (from patterns.json)
      - berth_flexibility (from patterns.json)
      - historical_turnaround (from patterns.json)
    """

    def __init__(self):
        if _HAS_XGB:
            self.model = XGBClassifier(
                n_estimators=150,
                max_depth=6,
                learning_rate=0.08,
                subsample=0.85,
                colsample_bytree=0.85,
                min_child_weight=3,
                eval_metric="mlogloss",
                use_label_encoder=False,
                # FIX (Phase 5): Use the shared deterministic seed across optional ranker backends.
                random_state=settings.ml_random_state,
                n_jobs=1,
                verbosity=0,
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                random_state=settings.ml_random_state,
                n_jobs=1,
            )
        self.label_encoder = LabelEncoder()
        self.metrics: Dict[str, float] = {}
        self.feature_importances_: Optional[Dict[str, float]] = None

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Train the ranker on historical data."""
        y_encoded = self.label_encoder.fit_transform(y)

        self.model.fit(X, y_encoded)

        # Cross-validation accuracy
        cv_scores = cross_val_score(self.model, X, y_encoded, cv=3, scoring="accuracy")
        self.metrics = {
            "accuracy": round(float(cv_scores.mean()), 4),
            "accuracy_std": round(float(cv_scores.std()), 4),
            "n_classes": len(self.label_encoder.classes_),
            "n_samples": len(X),
            "backend": "xgboost" if _HAS_XGB else "random_forest",
        }

        # Feature importance
        try:
            importances = self.model.feature_importances_
            self.feature_importances_ = {
                col: round(float(imp), 4)
                for col, imp in sorted(
                    zip(X.columns, importances),
                    key=lambda x: x[1],
                    reverse=True,
                )
            }
        except Exception:
            self.feature_importances_ = {}

        logger.info(
            "XGBoost ranker trained: accuracy=%.3f ±%.3f, %d classes, backend=%s",
            self.metrics["accuracy"],
            self.metrics["accuracy_std"],
            self.metrics["n_classes"],
            self.metrics["backend"],
        )
        return self.metrics

    def predict_proba_all(self, X: pd.DataFrame) -> Dict[str, float]:
        """
        For a single vessel feature row, return {berth_code: probability}.
        """
        probas = self.model.predict_proba(X)
        result = {}
        for i, cls in enumerate(self.label_encoder.classes_):
            prob = float(probas[0, i]) if probas.ndim == 2 else float(probas[i])
            result[str(cls)] = prob
        return result

    def predict_top_k(self, X: pd.DataFrame, k: int = 5) -> List[Tuple[str, float]]:
        """Return top-k berths with probabilities."""
        probas = self.model.predict_proba(X)
        if probas.ndim == 2:
            probas = probas[0]

        top_idx = np.argsort(probas)[::-1][:k]
        return [
            (str(self.label_encoder.classes_[i]), round(float(probas[i]), 4))
            for i in top_idx
            if probas[i] > 0.005
        ]

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate on a test set."""
        from sklearn.metrics import accuracy_score, top_k_accuracy_score

        # Only evaluate labels seen during training
        known_mask = y.isin(self.label_encoder.classes_)
        if known_mask.sum() == 0:
            return {"accuracy": 0.0, "top3_accuracy": 0.0}

        X_f = X[known_mask]
        y_f = y[known_mask]
        y_enc = self.label_encoder.transform(y_f)

        pred = self.model.predict(X_f)
        acc = accuracy_score(y_enc, pred)

        # Top-3 accuracy
        try:
            probas = self.model.predict_proba(X_f)
            top3_acc = top_k_accuracy_score(y_enc, probas, k=min(3, len(self.label_encoder.classes_)))
        except Exception:
            top3_acc = acc

        return {
            "accuracy": round(float(acc), 4),
            "top3_accuracy": round(float(top3_acc), 4),
        }

    def save(self, path: Path):
        """Persist model to disk."""
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "label_encoder": self.label_encoder,
                "metrics": self.metrics,
                "feature_importances": self.feature_importances_,
            }, f)
        # FIX (Phase 5): Ranker artifacts carry the same feature-extractor guard as core models.
        write_feature_hash(path)
        logger.info("Saved XGBoost ranker to %s", path)

    @classmethod
    def load(cls, path: Path) -> "XGBoostBerthRanker":
        """Load model from disk."""
        # FIX (Phase 5): Refuse stale ranker artifacts after feature extractor changes.
        verify_feature_hash(path)
        inst = cls.__new__(cls)
        with open(path, "rb") as f:
            data = pickle.load(f)
        inst.model = data["model"]
        inst.label_encoder = data["label_encoder"]
        inst.metrics = data.get("metrics", {})
        inst.feature_importances_ = data.get("feature_importances", {})
        return inst
