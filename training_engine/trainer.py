"""
Trainer — Training Engine Layer 2
Orchestrates the full training pipeline for a port.

Phase 2 Enhancements:
  - Stratified train/val/test split (70/15/15)
  - Evaluation metrics w/ uncertainty coverage
  - Model versioning (timestamped saves + comparison)
  - Feature importance reporting
"""
from __future__ import annotations
import json, sys, time, shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_layer.port_store import load_history, load_port_config, get_models_dir, is_trained
from training_engine.feature_builder import build_training_features
from training_engine.ml_models import (
    ServiceTimePredictor,
    BerthSuitabilityModel,
    DelayPredictor,
    DecisionRanker,
)


def train_port_models(port_name: str, test_size: float = 0.15, val_size: float = 0.15) -> dict:
    """
    Full training pipeline for a port:
    1. Load history + config
    2. Feature engineering (Phase 2 enhanced)
    3. Train/val/test split (stratified by berth when possible)
    4. Train 4 models with uncertainty
    5. Evaluate on test set (including uncertainty coverage)
    6. Save models + metadata with versioning
    """
    start_time = time.time()

    # Load data
    df_history = load_history(port_name)
    port_config = load_port_config(port_name)

    # Feature engineering (Phase 2 enhanced features)
    X, y_berth, y_service, y_delay = build_training_features(df_history, port_config)

    # ── Stratified Split: train(70%) / val(15%) / test(15%) ──
    # Stratify by berth code when possible
    berth_counts = y_berth.value_counts()
    stratify_col = y_berth if y_berth.nunique() >= 3 and berth_counts.min() >= 2 else None

    X_trainval, X_test, yb_trainval, yb_test, ys_trainval, ys_test, yd_trainval, yd_test = \
        train_test_split(
            X, y_berth, y_service, y_delay,
            test_size=test_size, random_state=42,
            stratify=stratify_col,
        )

    # Split train into train + val
    trainval_counts = yb_trainval.value_counts()
    strat_trainval = (
        yb_trainval
        if yb_trainval.nunique() >= 3 and trainval_counts.min() >= 2
        else None
    )
    val_frac = val_size / (1.0 - test_size)  # Adjust for remaining data
    X_train, X_val, yb_train, yb_val, ys_train, ys_val, yd_train, yd_val = \
        train_test_split(
            X_trainval, yb_trainval, ys_trainval, yd_trainval,
            test_size=val_frac, random_state=42,
            stratify=strat_trainval,
        )

    # Align feature columns
    for col in X_train.columns:
        if col not in X_val.columns:
            X_val[col] = 0
        if col not in X_test.columns:
            X_test[col] = 0
    X_val = X_val[X_train.columns]
    X_test = X_test[X_train.columns]

    models_dir = get_models_dir(port_name)
    results = {}

    # ── 1. Service Time Predictor (with quantile regression) ──
    stp = ServiceTimePredictor()
    stp.train(X_train, ys_train)
    stp_val = stp.evaluate(X_val, ys_val)
    stp_test = stp.evaluate(X_test, ys_test)
    stp.save(models_dir / "service_time.pkl")
    results["service_time"] = {
        **stp.metrics,
        "val": stp_val,
        "test": stp_test,
        "top_features": [
            {"feature": f, "importance": round(imp, 4)}
            for f, imp in stp.get_top_features(8)
        ],
    }

    # ── 2. Berth Suitability Model (with top-3 accuracy) ──
    bsm = BerthSuitabilityModel()
    bsm.train(X_train, yb_train)
    bsm_val = bsm.evaluate(X_val, yb_val)
    bsm_test = bsm.evaluate(X_test, yb_test)
    bsm.save(models_dir / "berth_suitability.pkl")
    results["berth_suitability"] = {
        **bsm.metrics,
        "val": bsm_val,
        "test": bsm_test,
        "top_features": [
            {"feature": f, "importance": round(imp, 4)}
            for f, imp in bsm.get_top_features(8)
        ],
    }

    # ── 3. Delay Predictor (with quantile regression) ──
    dp = DelayPredictor()
    dp.train(X_train, yd_train)
    dp_val = dp.evaluate(X_val, yd_val)
    dp_test = dp.evaluate(X_test, yd_test)
    dp.save(models_dir / "delay_predictor.pkl")
    results["delay_predictor"] = {
        **dp.metrics,
        "val": dp_val,
        "test": dp_test,
        "top_features": [
            {"feature": f, "importance": round(imp, 4)}
            for f, imp in dp.get_top_features(8)
        ],
    }

    # ── 4. Decision Ranker ──
    dr = DecisionRanker()
    dr.save(models_dir / "decision_ranker.pkl")
    results["decision_ranker"] = {
        "weights": {"suitability": dr.w_s, "wait": dr.w_w, "service": dr.w_v},
    }

    # ── Save feature column list ──
    feature_cols = X_train.columns.tolist()
    with open(models_dir / "feature_columns.json", "w") as f:
        json.dump(feature_cols, f)

    # ── Save metadata with versioning ──
    elapsed = time.time() - start_time
    version_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    metadata = {
        "port_name": port_name,
        "version": version_tag,
        "trained_at": datetime.utcnow().isoformat(),
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "test_samples": len(X_test),
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "elapsed_seconds": round(elapsed, 2),
        "split_ratios": {
            "train": round(len(X_train) / len(X), 2),
            "val": round(len(X_val) / len(X), 2),
            "test": round(len(X_test) / len(X), 2),
        },
        "results": results,
    }

    # Save current metadata
    with open(models_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # Save versioned copy for history tracking
    version_dir = models_dir / "versions"
    version_dir.mkdir(exist_ok=True)
    with open(version_dir / f"metadata_{version_tag}.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    return metadata
