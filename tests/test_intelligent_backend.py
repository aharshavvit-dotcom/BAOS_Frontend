"""
Intelligent Backend Enhancement — Test Suite

Tests covering:
  - Pattern Discovery Engine
  - XGBoost Berth Ranker
  - Enhanced Recommender hybrid scoring
  - Commercial objective terms in CP-SAT
  - Weekly refresh validation logic
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
import pandas as pd

# Setup path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Pattern Discovery Tests ────────────────────────────────────────────

class TestPatternDiscovery:
    """Tests for training_engine/pattern_discovery.py."""

    def _make_sample_df(self) -> pd.DataFrame:
        """Create a sample historical DataFrame."""
        np.random.seed(42)
        n = 200
        berths = ["BD1", "BD2", "CTB1", "CTB2", "GC1"]
        vtypes = ["Bulk dry", "Container", "General cargo", "Tanker"]
        data = {
            "berthcode": [],
            "vesseltype": [],
            "loa": np.random.uniform(100, 300, n).tolist(),
            "adraft": np.random.uniform(5, 14, n).tolist(),
            "dwt": np.random.uniform(5000, 80000, n).tolist(),
            "berth_occupancy_h": np.random.uniform(8, 72, n).tolist(),
        }
        # Create realistic patterns: Bulk dry mostly goes to BD1/BD2
        for i in range(n):
            vt = vtypes[i % len(vtypes)]
            data["vesseltype"].append(vt)
            if vt == "Bulk dry":
                data["berthcode"].append(np.random.choice(["BD1", "BD2"], p=[0.7, 0.3]))
            elif vt == "Container":
                data["berthcode"].append(np.random.choice(["CTB1", "CTB2"], p=[0.6, 0.4]))
            elif vt == "General cargo":
                data["berthcode"].append(np.random.choice(berths))
            else:
                data["berthcode"].append(np.random.choice(["BD1", "GC1"]))
        return pd.DataFrame(data)

    def test_compute_specialization(self):
        from engines.learning.training.pattern_discovery import _compute_specialization

        df = self._make_sample_df()
        df["_berth"] = df["berthcode"]
        df["_vtype"] = df["vesseltype"]
        result = _compute_specialization(df)

        assert "Bulk dry" in result, "Should have Bulk dry specialization"
        assert "Container" in result, "Should have Container specialization"
        # Bulk dry should score higher on BD1/BD2
        bulk_scores = result["Bulk dry"]
        assert bulk_scores.get("BD1", 0) > bulk_scores.get("GC1", 0), \
            "Bulk dry should prefer BD1 over GC1"

    def test_compute_factor_importance(self):
        from engines.learning.training.pattern_discovery import _compute_factor_importance

        df = self._make_sample_df()
        result = _compute_factor_importance(df, "berthcode", "vesseltype", "loa", "adraft")

        assert "vessel_type" in result, "Should include vessel_type factor"
        assert "loa" in result, "Should include LOA factor"
        assert sum(result.values()) == pytest.approx(1.0, abs=0.01), \
            "Factor importances should sum to ~1.0"

    def test_detect_constraints(self):
        from engines.learning.training.pattern_discovery import _compute_specialization, _detect_constraints

        df = self._make_sample_df()
        df["_berth"] = df["berthcode"]
        df["_vtype"] = df["vesseltype"]
        spec = _compute_specialization(df)
        constraints = _detect_constraints(df, spec)

        assert isinstance(constraints, list), "Should return a list of constraints"
        # With our biased data, we should detect at least one constraint
        types_found = {c.get("type") for c in constraints}
        assert len(constraints) > 0, "Should detect at least one constraint"

    def test_profile_berths(self):
        from engines.learning.training.pattern_discovery import _profile_berths

        df = self._make_sample_df()
        df["_berth"] = df["berthcode"]
        df["_vtype"] = df["vesseltype"]
        result = _profile_berths(df, "berth_occupancy_h")

        assert len(result) > 0, "Should profile at least one berth"
        for bc, info in result.items():
            assert "dominant_type" in info
            assert "flexibility" in info
            assert info["flexibility"] in ("highly_specialized", "moderately_specialized", "flexible")

    def test_cramers_v(self):
        from engines.learning.training.pattern_discovery import _cramers_v

        # Perfectly correlated
        x = pd.Series(["A", "A", "B", "B", "C", "C"])
        y = pd.Series(["X", "X", "Y", "Y", "Z", "Z"])
        v = _cramers_v(x, y)
        assert v > 0.8, f"Perfect correlation should give high V, got {v}"

        # Random
        x2 = pd.Series(["A", "B", "A", "B", "A", "B"])
        y2 = pd.Series(["X", "X", "Y", "Y", "X", "Y"])
        v2 = _cramers_v(x2, y2)
        assert v2 < v, "Random should have lower V than perfect correlation"


# ── XGBoost Ranker Tests ───────────────────────────────────────────────

class TestXGBoostRanker:
    """Tests for training_engine/xgboost_ranker.py."""

    def _make_training_data(self):
        np.random.seed(42)
        n = 100
        X = pd.DataFrame({
            "loa": np.random.uniform(100, 300, n),
            "draft": np.random.uniform(5, 14, n),
            "dwt": np.random.uniform(5000, 80000, n),
            "beam": np.random.uniform(15, 50, n),
            "cargo_tons": np.random.uniform(1000, 50000, n),
        })
        berths = ["BD1", "BD2", "CTB1", "GC1"]
        y = pd.Series([berths[i % len(berths)] for i in range(n)])
        return X, y

    def test_train_and_predict(self):
        from engines.learning.training.xgboost_ranker import XGBoostBerthRanker

        X, y = self._make_training_data()
        ranker = XGBoostBerthRanker()
        metrics = ranker.train(X, y)

        assert "accuracy" in metrics, "Should report accuracy"
        assert metrics["accuracy"] > 0, "Accuracy should be positive"

        # Predict probabilities
        sample = X.iloc[:1]
        proba = ranker.predict_proba_all(sample)
        assert len(proba) > 0, "Should return probabilities"
        assert all(0 <= v <= 1 for v in proba.values()), "Probabilities should be [0,1]"

    def test_predict_top_k(self):
        from engines.learning.training.xgboost_ranker import XGBoostBerthRanker

        X, y = self._make_training_data()
        ranker = XGBoostBerthRanker()
        ranker.train(X, y)

        top = ranker.predict_top_k(X.iloc[:1], k=3)
        assert len(top) > 0, "Should return at least 1 prediction"
        assert len(top) <= 3, "Should return at most k predictions"
        # Each element should be (berth_code, probability)
        for bc, prob in top:
            assert isinstance(bc, str)
            assert 0 <= prob <= 1

    def test_save_and_load(self, tmp_path):
        from engines.learning.training.xgboost_ranker import XGBoostBerthRanker

        X, y = self._make_training_data()
        ranker = XGBoostBerthRanker()
        ranker.train(X, y)

        path = tmp_path / "test_ranker.pkl"
        ranker.save(path)

        loaded = XGBoostBerthRanker.load(path)
        assert loaded.metrics["accuracy"] == ranker.metrics["accuracy"]

        # Predictions should match
        orig = ranker.predict_proba_all(X.iloc[:1])
        new = loaded.predict_proba_all(X.iloc[:1])
        for bc in orig:
            assert abs(orig[bc] - new[bc]) < 1e-6

    def test_evaluate(self):
        from engines.learning.training.xgboost_ranker import XGBoostBerthRanker

        X, y = self._make_training_data()
        ranker = XGBoostBerthRanker()
        ranker.train(X, y)

        eval_result = ranker.evaluate(X, y)
        assert "accuracy" in eval_result
        assert "top3_accuracy" in eval_result
        assert eval_result["top3_accuracy"] >= eval_result["accuracy"]



# ── Commercial CP-SAT Objective Tests ──────────────────────────────────

class TestCommercialObjective:
    """Tests for commercial terms in constraint_model.py."""

    def test_scheduler_config_has_commercial_fields(self):
        from engines.simulation.optimization.constraint_model import SchedulerConfig

        cfg = SchedulerConfig()
        assert hasattr(cfg, "w_commercial"), "Should have w_commercial field"
        assert hasattr(cfg, "w_partnership"), "Should have w_partnership field"
        assert hasattr(cfg, "decision_mode"), "Should have decision_mode field"
        assert cfg.w_commercial == 0.0, "w_commercial should default to 0"
        assert cfg.w_partnership == 0.0, "w_partnership should default to 0"
        assert cfg.decision_mode == "technical_only"

    def test_commercial_config_modes(self):
        from engines.simulation.optimization.constraint_model import SchedulerConfig

        # Revenue first mode
        revenue_cfg = SchedulerConfig(
            w_commercial=1.5,
            w_partnership=0.3,
            decision_mode="revenue_first",
        )
        assert revenue_cfg.w_commercial == 1.5
        assert revenue_cfg.decision_mode == "revenue_first"

        # Partnership focused mode
        partner_cfg = SchedulerConfig(
            w_commercial=0.5,
            w_partnership=2.0,
            decision_mode="partnership_focused",
        )
        assert partner_cfg.w_partnership == 2.0

    def test_build_objective_with_commercial_terms(self):
        """Verify the CP-SAT model builds successfully with commercial weights."""
        from engines.simulation.optimization.constraint_model import (
            BerthConstraintModel, VesselInput, BerthInput, SchedulerConfig,
        )

        vessels = [
            VesselInput(
                vessel_id="V1", name="Test Ship",
                vessel_type="Bulk dry", cargo_type="Coal",
                loa_m=180, beam_m=28, draft_m=10,
                priority=50,  # VIP vessel
            ),
        ]
        berths = [
            BerthInput(
                berth_code="BD1", berth_name="Berth D1",
                max_loa_m=250, max_beam_m=40, max_draft_m=14,
                allowed_vessel_types=["Bulk dry"],
                equipment_types=["crane", "conveyor"],
            ),
        ]

        # Enable commercial terms
        cfg = SchedulerConfig(
            w_commercial=1.0,
            w_partnership=0.8,
            decision_mode="balanced",
        )

        model = BerthConstraintModel(vessels, berths, cfg)
        model.add_physical_constraints()
        model.add_temporal_constraints()
        model.add_policy_constraints()

        # Solve should succeed
        result = model.solve()
        assert result.status_name in ("OPTIMAL", "FEASIBLE"), \
            f"Solver should find solution, got {result.status_name}"


# ── Weekly Refresh Tests ───────────────────────────────────────────────

class TestWeeklyRefresh:
    """Tests for learning_engine/weekly_refresh.py."""

    def test_compare_metrics_improved(self):
        from engines.learning.weekly_refresh import _compare_metrics

        old = {
            "results": {
                "berth_suitability": {"test": {"accuracy": 0.75}},
                "service_time": {"test": {"mae": 5.0}},
                "xgboost_ranker": {"test": {"accuracy": 0.70}},
            }
        }
        new = {
            "results": {
                "berth_suitability": {"test": {"accuracy": 0.80}},
                "service_time": {"test": {"mae": 4.5}},
                "xgboost_ranker": {"test": {"accuracy": 0.75}},
            }
        }
        comparison = _compare_metrics(old, new)
        assert comparison["improved"] is True
        assert comparison["suitability_delta"] == pytest.approx(0.05)

    def test_compare_metrics_degraded(self):
        from engines.learning.weekly_refresh import _compare_metrics

        old = {
            "results": {
                "berth_suitability": {"test": {"accuracy": 0.85}},
                "service_time": {"test": {"mae": 3.0}},
                "xgboost_ranker": {"test": {"accuracy": 0.80}},
            }
        }
        new = {
            "results": {
                "berth_suitability": {"test": {"accuracy": 0.60}},
                "service_time": {"test": {"mae": 8.0}},
                "xgboost_ranker": {"test": {"accuracy": 0.55}},
            }
        }
        comparison = _compare_metrics(old, new)
        assert comparison["improved"] is False

    def test_compare_no_baseline(self):
        from engines.learning.weekly_refresh import _compare_metrics

        comparison = _compare_metrics(None, {"results": {}})
        assert comparison["improved"] is True
        assert comparison["reason"] == "no_prior_baseline"
