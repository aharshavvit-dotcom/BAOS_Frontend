"""
Trainer — Training Engine Layer 2
Orchestrates the full training pipeline for a port.

Phase 2 Enhancements:
  - Stratified train/validation split (80/20)
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

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.config.settings import settings
from backend.db.repositories.port_store import load_history, load_port_config, get_models_dir, is_trained
from backend.utils.exceptions import InsufficientDataError
from engines.learning.training.feature_builder import build_training_features
from engines.learning.training.ml_models import (
    ServiceTimePredictor,
    BerthSuitabilityModel,
    DelayPredictor,
    DecisionRanker,
    compute_feature_hash,
)


def train_port_models(port_name: str, test_size: float = 0.0, val_size: float | None = None) -> dict:
    """
    Full training pipeline for a port:
    1. Load history + config
    2. Feature engineering (Phase 2 enhanced)
    3. Train/validation split (stratified by berth when possible)
    4. Train 4 models with uncertainty
    5. Evaluate on validation set
    6. Save models + metadata with versioning
    """
    start_time = time.time()

    # Load data
    df_history = load_history(port_name)
    port_config = load_port_config(port_name)

    # Feature engineering (Phase 2 enhanced features)
    X, y_berth, y_service, y_delay = build_training_features(df_history, port_config)

    if len(X) < settings.min_training_rows or y_berth.nunique() < 2:
        # FIX (Phase 5): Offline trainer uses the same minimum-data gate as the API trainer.
        raise InsufficientDataError(
            f"Insufficient training data: rows={len(X)} classes={y_berth.nunique()}"
        )

    validation_size = val_size if val_size is not None else settings.ml_validation_size
    # FIX (Phase 5): Use deterministic 80/20 train/validation split with no pseudo-test holdout.
    # Stratify by berth code when possible
    berth_counts = y_berth.value_counts()
    validation_rows = int(np.ceil(len(X) * validation_size))
    stratify_col = (
        y_berth
        if (
            y_berth.nunique() >= 3
            and berth_counts.min() >= 2
            and validation_rows >= y_berth.nunique()
            and (len(X) - validation_rows) >= y_berth.nunique()
        )
        else None
    )

    X_train, X_val, yb_train, yb_val, ys_train, ys_val, yd_train, yd_val = \
        train_test_split(
            X, y_berth, y_service, y_delay,
            test_size=validation_size, random_state=settings.ml_random_state,
            stratify=stratify_col,
        )

    # Align feature columns
    for col in X_train.columns:
        if col not in X_val.columns:
            X_val[col] = 0
    X_val = X_val[X_train.columns]

    models_dir = get_models_dir(port_name)
    results = {}

    # ── 1. Service Time Predictor (with quantile regression) ──
    stp = ServiceTimePredictor()
    stp.train(X_train, ys_train)
    stp_train = stp.evaluate(X_train, ys_train)
    stp_val = stp.evaluate(X_val, ys_val)
    stp.save(models_dir / "service_time.pkl")
    results["service_time"] = {
        **stp.metrics,
        "train": stp_train,
        "val": stp_val,
        "top_features": [
            {"feature": f, "importance": round(imp, 4)}
            for f, imp in stp.get_top_features(8)
        ],
    }

    # ── 2. Berth Suitability Model (with top-3 accuracy) ──
    bsm = BerthSuitabilityModel()
    bsm.train(X_train, yb_train)
    bsm_train = bsm.evaluate(X_train, yb_train)
    bsm_val = bsm.evaluate(X_val, yb_val)
    bsm.save(models_dir / "berth_suitability.pkl")
    results["berth_suitability"] = {
        **bsm.metrics,
        "train": bsm_train,
        "val": bsm_val,
        "top_features": [
            {"feature": f, "importance": round(imp, 4)}
            for f, imp in bsm.get_top_features(8)
        ],
    }

    # ── 3. Delay Predictor (with quantile regression) ──
    dp = DelayPredictor()
    dp.train(X_train, yd_train)
    dp_train = dp.evaluate(X_train, yd_train)
    dp_val = dp.evaluate(X_val, yd_val)
    dp.save(models_dir / "delay_predictor.pkl")
    results["delay_predictor"] = {
        **dp.metrics,
        "train": dp_train,
        "val": dp_val,
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
        "total_samples": len(X),
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "test_samples": 0,
        "feature_hash": compute_feature_hash(),
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "removed_leakage_features": ["ddraught", "cargo_handling_rate"],
        "elapsed_seconds": round(elapsed, 2),
        "split_ratios": {
            "train": round(len(X_train) / len(X), 2),
            "val": round(len(X_val) / len(X), 2),
            "test": 0.0,
        },
        "split_strategy": "train_val_80_20",
        "hyperparameters": settings.training_hyperparameters,
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
