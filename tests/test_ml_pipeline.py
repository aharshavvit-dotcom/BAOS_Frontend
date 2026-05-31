"""
Tests for Phase 2: ML Models Foundation
========================================
Validates:
  1. Feature builder produces expected feature columns
  2. Cyclical time encoding is correct
  3. ServiceTimePredictor quantile regression
  4. DelayPredictor quantile regression
  5. BerthSuitabilityModel top-3 accuracy
  6. DecisionRanker with uncertainty data
  7. Full training pipeline (if history exists)
  8. UI components import cleanly
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.learning.training.feature_builder import (
    VESSEL_FEATURES, CONTEXT_FEATURES, BERTH_FEATURES, DERIVED_FEATURES,
    build_training_features, build_inference_features,
    _cyclical_encode,
)
from engines.learning.training.ml_models import (
    ServiceTimePredictor, BerthSuitabilityModel,
    DelayPredictor, DecisionRanker, QuantilePrediction,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_history_df(n=100):
    """Generate a minimal history DataFrame for testing."""
    np.random.seed(42)
    berths = ["NCB1", "NCB2", "NCB3", "WQ1", "WQ2"]
    vessel_types = ["BULK CARRIER", "CONTAINER", "TANKER", "GENERAL CARGO"]

    df = pd.DataFrame({
        "berthcode": np.random.choice(berths, n),
        "vesseltype": np.random.choice(vessel_types, n),
        "loa": np.random.uniform(100, 300, n),
        "adraft": np.random.uniform(5, 15, n),
        "ddraught": np.random.uniform(5, 15, n),
        "dwt": np.random.uniform(5000, 80000, n),
        "berth_occupancy_h": np.random.uniform(6, 72, n),
        "pilot_wait_h": np.random.exponential(2, n),
        "eta": pd.date_range("2025-06-01", periods=n, freq="8h"),
    })
    return df


def _make_port_config():
    """Generate a minimal port config for testing."""
    return {
        "berths": [
            {"berth_code": "NCB1", "berth_name": "NCB-1", "max_loa_m": 250,
             "max_draft_m": 14, "depth_m": 16, "max_beam_m": 40,
             "equipment": ["crane", "conveyor"]},
            {"berth_code": "NCB2", "berth_name": "NCB-2", "max_loa_m": 200,
             "max_draft_m": 12, "depth_m": 14, "max_beam_m": 35,
             "equipment": ["crane"]},
            {"berth_code": "NCB3", "berth_name": "NCB-3", "max_loa_m": 180,
             "max_draft_m": 10, "depth_m": 12, "max_beam_m": 30,
             "equipment": ["crane", "hose"]},
            {"berth_code": "WQ1", "berth_name": "WQ-1", "max_loa_m": 300,
             "max_draft_m": 15, "depth_m": 18, "max_beam_m": 45,
             "equipment": ["crane", "conveyor", "gangway"]},
            {"berth_code": "WQ2", "berth_name": "WQ-2", "max_loa_m": 280,
             "max_draft_m": 14, "depth_m": 16, "max_beam_m": 42,
             "equipment": ["hose", "gangway"]},
        ],
        "service_time_stats": [
            {"berth_code": "NCB1", "vessel_type": "BULK CARRIER",
             "service_hours_median": 24.0},
        ],
    }


# ══════════════════════════════════════════════════════════════════════════
#  TEST 1: Feature Builder
# ══════════════════════════════════════════════════════════════════════════

def test_feature_columns():
    """Feature builder produces all expected columns."""
    df = _make_history_df()
    cfg = _make_port_config()
    X, y_berth, y_service, y_delay = build_training_features(df, cfg)

    # Check all base feature groups are present
    for col in VESSEL_FEATURES:
        assert col in X.columns, f"Missing vessel feature: {col}"
    for col in CONTEXT_FEATURES:
        assert col in X.columns, f"Missing context feature: {col}"
    for col in BERTH_FEATURES:
        assert col in X.columns, f"Missing berth feature: {col}"
    for col in DERIVED_FEATURES:
        assert col in X.columns, f"Missing derived feature: {col}"

    # Phase 2 new features must exist
    assert "beam" in X.columns, "Missing beam feature"
    assert "hour_sin" in X.columns, "Missing cyclical hour_sin"
    assert "hour_cos" in X.columns, "Missing cyclical hour_cos"
    assert "equipment_match_score" in X.columns, "Missing equipment_match_score"
    assert "berth_specialization_ratio" in X.columns, "Missing berth_specialization_ratio"
    assert "beam_berth_ratio" in X.columns, "Missing beam_berth_ratio"

    # Check no NaN
    assert X.isna().sum().sum() == 0, f"NaN found in features: {X.isna().sum()[X.isna().sum() > 0]}"


def test_cyclical_encoding():
    """Cyclical encoding produces correct sin/cos values."""
    vals = pd.Series([0, 6, 12, 18, 24])
    sin_v, cos_v = _cyclical_encode(vals, 24.0)

    # At 0h: sin=0, cos=1
    assert abs(sin_v.iloc[0]) < 0.01, f"sin(0) should be ~0, got {sin_v.iloc[0]}"
    assert abs(cos_v.iloc[0] - 1.0) < 0.01, f"cos(0) should be ~1, got {cos_v.iloc[0]}"

    # At 6h: sin=1, cos=0
    assert abs(sin_v.iloc[1] - 1.0) < 0.01, f"sin(6h) should be ~1, got {sin_v.iloc[1]}"

    # At 12h: sin=0, cos=-1
    assert abs(sin_v.iloc[2]) < 0.01, f"sin(12h) should be ~0, got {sin_v.iloc[2]}"

    # At 24h: wraps back to same as 0h
    assert abs(sin_v.iloc[4] - sin_v.iloc[0]) < 0.01, "24h should wrap to 0h"


def test_inference_features_match_training():
    """Inference features produce same columns as training features."""
    vessel = {
        "loa": 180, "draft": 10, "beam": 28, "dwt": 30000,
        "vessel_type": "BULK CARRIER", "cargo_tons": 25000,
    }
    berth = {
        "berth_code": "NCB1", "max_loa_m": 250, "max_draft_m": 14,
        "depth_m": 16, "max_beam_m": 40, "equipment": ["crane", "conveyor"],
    }
    cfg = _make_port_config()

    X_inf = build_inference_features(vessel, berth, cfg)

    # All base features must be present
    all_features = VESSEL_FEATURES + CONTEXT_FEATURES + BERTH_FEATURES + DERIVED_FEATURES
    for col in all_features:
        assert col in X_inf.columns, f"Missing inference feature: {col}"


# ══════════════════════════════════════════════════════════════════════════
#  TEST 2: ServiceTimePredictor with Quantile Regression
# ══════════════════════════════════════════════════════════════════════════

def test_service_time_quantile():
    """ServiceTimePredictor produces uncertainty bounds."""
    df = _make_history_df(200)
    cfg = _make_port_config()
    X, _, y_service, _ = build_training_features(df, cfg)

    stp = ServiceTimePredictor()
    stp.train(X, y_service)

    # Point prediction (backward compatible)
    pred = stp.predict(X[:5])
    assert len(pred) == 5, f"Expected 5 predictions, got {len(pred)}"
    assert all(p >= 0.5 for p in pred), "All predictions should be >= 0.5"

    # Quantile prediction
    quant = stp.predict_with_uncertainty(X[:5])
    assert len(quant) == 5, f"Expected 5 quantile predictions, got {len(quant)}"

    for q in quant:
        assert isinstance(q, QuantilePrediction)
        assert q.lower <= q.point, f"Lower ({q.lower}) should be <= point ({q.point})"
        assert q.point <= q.upper, f"Point ({q.point}) should be <= upper ({q.upper})"
        assert q.confidence_width >= 0, "Confidence width should be >= 0"

    # Feature importance
    top_feats = stp.get_top_features(5)
    assert len(top_feats) > 0, "Should have feature importances"
    assert all(imp >= 0 for _, imp in top_feats), "Importances should be non-negative"

    # Metrics
    assert "mae" in stp.metrics
    assert "r2" in stp.metrics


def test_service_time_evaluate_coverage():
    """Evaluate method includes coverage metric."""
    df = _make_history_df(200)
    cfg = _make_port_config()
    X, _, y_service, _ = build_training_features(df, cfg)

    stp = ServiceTimePredictor()
    stp.train(X, y_service)
    eval_result = stp.evaluate(X[:50], y_service[:50])

    assert "mae" in eval_result
    assert "coverage_pct" in eval_result
    assert "avg_uncertainty_width_h" in eval_result
    # Coverage should be reasonable (not 0% or negative)
    assert eval_result["coverage_pct"] >= 0, f"Coverage should be >= 0, got {eval_result['coverage_pct']}"


# ══════════════════════════════════════════════════════════════════════════
#  TEST 3: DelayPredictor with Quantile Regression
# ══════════════════════════════════════════════════════════════════════════

def test_delay_quantile():
    """DelayPredictor produces uncertainty bounds."""
    df = _make_history_df(200)
    cfg = _make_port_config()
    X, _, _, y_delay = build_training_features(df, cfg)

    dp = DelayPredictor()
    dp.train(X, y_delay)

    quant = dp.predict_with_uncertainty(X[:5])
    assert len(quant) == 5

    for q in quant:
        assert q.lower <= q.point + 0.01  # Allow tiny float error
        assert q.point <= q.upper + 0.01

    # Feature importance
    top_feats = dp.get_top_features(5)
    assert len(top_feats) > 0


# ══════════════════════════════════════════════════════════════════════════
#  TEST 4: BerthSuitabilityModel with top-3 accuracy
# ══════════════════════════════════════════════════════════════════════════

def test_suitability_top3():
    """BerthSuitabilityModel tracks top-3 accuracy."""
    df = _make_history_df(200)
    cfg = _make_port_config()
    X, y_berth, _, _ = build_training_features(df, cfg)

    bsm = BerthSuitabilityModel()
    bsm.train(X, y_berth)

    # Evaluate with top-3
    eval_result = bsm.evaluate(X[:50], y_berth[:50])
    assert "top3_accuracy" in eval_result, "Should include top3_accuracy"
    assert eval_result["top3_accuracy"] >= eval_result["accuracy"], (
        "Top-3 accuracy should be >= top-1 accuracy"
    )

    # Feature importance
    top_feats = bsm.get_top_features(5)
    assert len(top_feats) > 0


# ══════════════════════════════════════════════════════════════════════════
#  TEST 5: DecisionRanker with uncertainty
# ══════════════════════════════════════════════════════════════════════════

def test_ranker_with_uncertainty():
    """DecisionRanker uses uncertainty data."""
    suit_scores = {"B1": 0.8, "B2": 0.6, "B3": 0.4}
    wait_pred = {"B1": 2.0, "B2": 3.0, "B3": 1.0}
    svc_pred = {"B1": 24.0, "B2": 18.0, "B3": 36.0}
    berth_info = {
        "B1": {"berth_name": "Berth 1"},
        "B2": {"berth_name": "Berth 2"},
        "B3": {"berth_name": "Berth 3"},
    }

    svc_uncert = {
        "B1": QuantilePrediction(point=24, lower=20, upper=28, confidence_width=8),
        "B2": QuantilePrediction(point=18, lower=15, upper=22, confidence_width=7),
        "B3": QuantilePrediction(point=36, lower=10, upper=60, confidence_width=50),  # High uncertainty
    }

    dr = DecisionRanker()
    options = dr.rank(
        suit_scores, wait_pred, svc_pred, berth_info,
        top_k=3,
        service_uncertainty=svc_uncert,
    )

    assert len(options) == 3
    assert options[0].rank == 1
    assert options[0].berth_code == "B1"  # Highest suitability

    # Check uncertainty bounds are populated
    for opt in options:
        assert opt.service_time_lower > 0
        assert opt.service_time_upper >= opt.service_time_lower


# ══════════════════════════════════════════════════════════════════════════
#  TEST 6: BerthOption has new uncertainty fields
# ══════════════════════════════════════════════════════════════════════════

def test_berth_option_fields():
    """BerthOption includes Phase 2 uncertainty fields."""
    from engines.learning.training.ml_models import BerthOption
    opt = BerthOption(
        berth_code="B1", berth_name="Test",
        service_time_lower=20.0, service_time_upper=28.0,
        delay_lower=1.0, delay_upper=3.5,
    )
    assert opt.service_time_lower == 20.0
    assert opt.service_time_upper == 28.0
    assert opt.delay_lower == 1.0
    assert opt.delay_upper == 3.5


# ══════════════════════════════════════════════════════════════════════════
#  TEST 7: Full Training Pipeline
# ══════════════════════════════════════════════════════════════════════════

def test_training_pipeline():
    """Full training pipeline runs successfully (if port data exists)."""
    from backend.db.repositories.port_store import port_exists
    if not port_exists("chennai"):
        return  # Skip if no port data

    from engines.learning.training.trainer import train_port_models
    metadata = train_port_models("chennai")

    assert metadata["training_samples"] > 0
    assert metadata["feature_count"] > 10
    assert "version" in metadata
    assert "split_ratios" in metadata

    # Check all models have results
    for model_key in ["service_time", "berth_suitability", "delay_predictor"]:
        assert model_key in metadata["results"], f"Missing {model_key} results"
        assert "val" in metadata["results"][model_key], f"Missing val metrics for {model_key}"

    # Feature importance should be present
    stp_res = metadata["results"]["service_time"]
    assert "top_features" in stp_res
    assert len(stp_res["top_features"]) > 0


# ══════════════════════════════════════════════════════════════════════════
#  TEST 8: UI Components Import
# ══════════════════════════════════════════════════════════════════════════

def test_ui_import():
    """Core explanation engine components can be imported (Next.js app — no Streamlit UI)."""
    from engines.analytics.explanation.structured_explanation import StructuredExplanationEngine
    from engines.analytics.explanation.explainer import AgenticExplainer
    # Just verify they're callable / importable
    assert callable(StructuredExplanationEngine)
    assert callable(AgenticExplainer)


# ══════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    ("Feature Columns", test_feature_columns),
    ("Cyclical Encoding", test_cyclical_encoding),
    ("Inference Features Match", test_inference_features_match_training),
    ("Service Time Quantile", test_service_time_quantile),
    ("Service Time Coverage", test_service_time_evaluate_coverage),
    ("Delay Quantile", test_delay_quantile),
    ("Suitability Top-3", test_suitability_top3),
    ("Ranker With Uncertainty", test_ranker_with_uncertainty),
    ("BerthOption Fields", test_berth_option_fields),
    ("Training Pipeline", test_training_pipeline),
    ("UI Components Import", test_ui_import),
]

if __name__ == "__main__":
    import traceback

    passed = 0
    failed = 0
    for name, fn in ALL_TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name} -- {e}")
            traceback.print_exc()

    print(f"\nPhase 2 ML Tests: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    sys.exit(1 if failed > 0 else 0)
