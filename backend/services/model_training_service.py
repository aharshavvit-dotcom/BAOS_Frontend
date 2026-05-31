"""
Startup ML training orchestration.

The backend owns model readiness. On startup it inspects baos.port_call,
baos.berth and baos.berth_capability, then trains and registers required
models when valid data exists and active models are missing or stale.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.db.models.baos_models import (
    BaosBerth,
    BaosBerthCapability,
    BaosMLModelRegistry,
    BaosPort,
    BaosPortCall,
    TrainingRun,
)
from backend.db.repositories.model_registry_repository import get_active_model, register_model
from backend.db.repositories.port_repository import get_port_by_code, list_ports
from backend.db.session import async_session_factory
from backend.services.port_config_service import load_port_config_from_db
from backend.services.training_data_service import load_history_from_db
from backend.utils.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


_training_lock = asyncio.Lock()
_training_in_progress = False

MIN_VALID_TRAINING_ROWS = settings.min_training_rows
MIN_BERTH_CLASSES = 2
REQUIRED_MODELS = {
    "berth_suitability": {
        "model_type": "classifier",
        "target_name": "berth_code",
        "artifact_file": "berth_suitability.pkl",
        "metadata_key": "berth_suitability",
    },
    "service_time_predictor": {
        "model_type": "regressor",
        "target_name": "berth_occupancy_hours",
        "artifact_file": "service_time.pkl",
        "metadata_key": "service_time",
    },
    "delay_predictor": {
        "model_type": "regressor",
        "target_name": "pilot_wait_hours",
        "artifact_file": "delay_predictor.pkl",
        "metadata_key": "delay_predictor",
    },
}


@dataclass(frozen=True)
class TrainingStatusValue:
    code: str
    label: str


DATA_MISSING = TrainingStatusValue("data_missing", "Data Missing")
TRAINING_PENDING = TrainingStatusValue("data_loaded_training_pending", "Data Loaded - Training Pending")
TRAINING_IN_PROGRESS = TrainingStatusValue("training_in_progress", "Training In Progress")
TRAINED = TrainingStatusValue("trained", "Trained")
TRAINING_FAILED = TrainingStatusValue("training_failed", "Training Failed")
INSUFFICIENT_DATA = TrainingStatusValue("insufficient_data", "Insufficient Data")


_runtime_status: dict[str, dict[str, Any]] = {}


class TrainingAlreadyInProgressError(RuntimeError):
    """Raised when a duplicate training request is rejected."""


def _primary_score(metrics: dict[str, Any], model_type: str, split: str) -> float | None:
    values = metrics.get(split, metrics)
    if not isinstance(values, dict):
        return None
    key = "accuracy" if model_type == "classifier" else "r2"
    value = values.get(key)
    return float(value) if value is not None else None


def get_training_lock_status() -> dict[str, bool]:
    return {
        "in_progress": _training_in_progress,
        "lock_held": _training_lock.locked(),
    }


def _train_port_models_from_data(port_code: str, df_history, port_config: dict) -> dict:
    import json
    import math
    import time

    from sklearn.model_selection import train_test_split

    from engines.learning.training.feature_builder import build_training_features
    from engines.learning.training.ml_models import (
        BerthSuitabilityModel,
        DecisionRanker,
        DelayPredictor,
        ServiceTimePredictor,
        compute_feature_hash,
    )

    start_time = time.time()
    X, y_berth, y_service, y_delay = build_training_features(df_history, port_config)

    if len(X) < settings.min_training_rows or y_berth.nunique() < MIN_BERTH_CLASSES:
        # FIX (Phase 5): Training data gates are explicit and configurable before artifacts are produced.
        raise InsufficientDataError(
            f"Insufficient training data: rows={len(X)} classes={y_berth.nunique()}"
        )

    berth_counts = y_berth.value_counts()
    validation_rows = math.ceil(len(X) * settings.ml_validation_size)
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
    # FIX (Phase 5): Use a deterministic train/validation split only; holdout testing was not real backtesting.
    X_train, X_val, yb_train, yb_val, ys_train, ys_val, yd_train, yd_val = train_test_split(
        X,
        y_berth,
        y_service,
        y_delay,
        test_size=settings.ml_validation_size,
        random_state=settings.ml_random_state,
        stratify=stratify_col,
    )

    for col in X_train.columns:
        if col not in X_val.columns:
            X_val[col] = 0
    X_val = X_val[X_train.columns]

    models_dir = Path("ports") / port_code.lower() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    feature_hash = compute_feature_hash()

    service_time = ServiceTimePredictor()
    service_time.train(X_train, ys_train)
    results["service_time"] = {
        **service_time.metrics,
        "train": service_time.evaluate(X_train, ys_train),
        "val": service_time.evaluate(X_val, ys_val),
        "top_features": [
            {"feature": feature, "importance": round(importance, 4)}
            for feature, importance in service_time.get_top_features(8)
        ],
    }
    service_time.save(models_dir / "service_time.pkl")

    berth_suitability = BerthSuitabilityModel()
    berth_suitability.train(X_train, yb_train)
    results["berth_suitability"] = {
        **berth_suitability.metrics,
        "train": berth_suitability.evaluate(X_train, yb_train),
        "val": berth_suitability.evaluate(X_val, yb_val),
        "top_features": [
            {"feature": feature, "importance": round(importance, 4)}
            for feature, importance in berth_suitability.get_top_features(8)
        ],
    }
    berth_suitability.save(models_dir / "berth_suitability.pkl")

    delay = DelayPredictor()
    delay.train(X_train, yd_train)
    results["delay_predictor"] = {
        **delay.metrics,
        "train": delay.evaluate(X_train, yd_train),
        "val": delay.evaluate(X_val, yd_val),
        "top_features": [
            {"feature": feature, "importance": round(importance, 4)}
            for feature, importance in delay.get_top_features(8)
        ],
    }
    delay.save(models_dir / "delay_predictor.pkl")

    ranker = DecisionRanker()
    ranker.save(models_dir / "decision_ranker.pkl")

    feature_cols = X_train.columns.tolist()
    (models_dir / "feature_columns.json").write_text(json.dumps(feature_cols), encoding="utf-8")

    version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    metadata = {
        "port_name": port_code,
        "version": version,
        "trained_at": datetime.utcnow().isoformat(),
        "total_samples": len(X),
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "test_samples": 0,
        "feature_hash": feature_hash,
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "removed_leakage_features": ["ddraught", "cargo_handling_rate"],
        "elapsed_seconds": round(time.time() - start_time, 2),
        "split_ratios": {
            "train": round(len(X_train) / len(X), 2),
            "val": round(len(X_val) / len(X), 2),
            "test": 0.0,
        },
        "split_strategy": "train_val_80_20",
        "hyperparameters": settings.training_hyperparameters,
        "results": results,
    }
    (models_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )
    versions_dir = models_dir / "versions"
    versions_dir.mkdir(exist_ok=True)
    (versions_dir / f"metadata_{version}.json").write_text(
        json.dumps(metadata, indent=2, default=str),
        encoding="utf-8",
    )
    return metadata


def _utcnow() -> datetime:
    return datetime.utcnow()


def _as_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(tz=None).replace(tzinfo=None)


def _set_runtime_status(port_code: str, status: TrainingStatusValue, message: str, **extra: Any) -> None:
    _runtime_status[port_code.upper()] = {
        **extra,
        "training_status": status.code,
        "status_label": status.label,
        "training_message": message,
        "updated_at": _utcnow().isoformat(),
    }


def get_training_status_snapshot(port_code: str) -> dict[str, Any] | None:
    status = _runtime_status.get(port_code.upper())
    return dict(status) if status else None


async def _count_scalar(db: AsyncSession, stmt) -> int:
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def _max_timestamp(db: AsyncSession, stmt) -> datetime | None:
    result = await db.execute(stmt)
    return _as_naive(result.scalar_one_or_none())


async def _latest_data_timestamp(db: AsyncSession, port_id) -> datetime | None:
    timestamps = [
        await _max_timestamp(
            db,
            select(func.max(BaosPortCall.updated_at)).where(BaosPortCall.port_id == port_id),
        ),
        await _max_timestamp(
            db,
            select(func.max(BaosBerth.updated_at)).where(BaosBerth.port_id == port_id),
        ),
        await _max_timestamp(
            db,
            select(func.max(BaosBerthCapability.updated_at))
            .join(BaosBerth, BaosBerthCapability.berth_id == BaosBerth.berth_id)
            .where(BaosBerth.port_id == port_id),
        ),
    ]
    real_timestamps = [ts for ts in timestamps if ts is not None]
    return max(real_timestamps) if real_timestamps else None


async def _data_date_range(db: AsyncSession, port_id) -> tuple[datetime | None, datetime | None]:
    result = await db.execute(
        select(func.min(BaosPortCall.eosp_ts), func.max(BaosPortCall.eosp_ts)).where(
            BaosPortCall.port_id == port_id,
            BaosPortCall.is_valid_for_training == True,  # noqa: E712
        )
    )
    row = result.one_or_none()
    if not row:
        return None, None
    return _as_naive(row[0]), _as_naive(row[1])


async def evaluate_port_training_status(db: AsyncSession, port_code: str) -> dict[str, Any]:
    normalized_port_code = port_code.strip().upper()
    port = await get_port_by_code(db, normalized_port_code)
    if port is None:
        return {
            "training_status": DATA_MISSING.code,
            "status_label": DATA_MISSING.label,
            "training_message": "Data Missing",
            "trained": False,
            "has_enough_data": False,
            "is_stale": False,
            "models_required": list(REQUIRED_MODELS),
            "models_active": [],
            "models_missing": list(REQUIRED_MODELS),
            "models_stale": [],
            "history_rows": 0,
            "valid_training_rows": 0,
            "berth_count": 0,
            "capability_count": 0,
            "berth_class_count": 0,
        }

    berth_count = await _count_scalar(
        db,
        select(func.count(BaosBerth.berth_id)).where(
            BaosBerth.port_id == port.port_id,
            BaosBerth.is_active == True,  # noqa: E712
        ),
    )
    capability_count = await _count_scalar(
        db,
        select(func.count(BaosBerthCapability.capability_id))
        .join(BaosBerth, BaosBerthCapability.berth_id == BaosBerth.berth_id)
        .where(BaosBerth.port_id == port.port_id),
    )
    history_rows = await _count_scalar(
        db,
        select(func.count(BaosPortCall.port_call_id)).where(BaosPortCall.port_id == port.port_id),
    )
    valid_rows = await _count_scalar(
        db,
        select(func.count(BaosPortCall.port_call_id)).where(
            BaosPortCall.port_id == port.port_id,
            BaosPortCall.is_valid_for_training == True,  # noqa: E712
        ),
    )
    berth_class_count = await _count_scalar(
        db,
        select(func.count(func.distinct(BaosPortCall.berth_code_raw))).where(
            BaosPortCall.port_id == port.port_id,
            BaosPortCall.is_valid_for_training == True,  # noqa: E712
            BaosPortCall.berth_code_raw.is_not(None),
        ),
    )
    latest_data_ts = await _latest_data_timestamp(db, port.port_id)
    data_start_ts, data_end_ts = await _data_date_range(db, port.port_id)

    active_models: dict[str, BaosMLModelRegistry] = {}
    for model_name in REQUIRED_MODELS:
        model = await get_active_model(db, normalized_port_code, model_name)
        if model is not None:
            active_models[model_name] = model

    active_names = sorted(active_models)
    missing_models = [name for name in REQUIRED_MODELS if name not in active_models]
    stale_models: list[str] = []
    if latest_data_ts is not None:
        from datetime import timezone
        for model_name, model in active_models.items():
            if model.created_at is None:
                stale_models.append(model_name)
                continue
            # FIX: model.created_at is naive UTC, latest_data_ts is naive local. Convert both to aware UTC for comparison.
            model_created_at_utc = model.created_at.replace(tzinfo=timezone.utc)
            latest_data_ts_utc = latest_data_ts.astimezone(timezone.utc)
            if model_created_at_utc < latest_data_ts_utc:
                stale_models.append(model_name)

    has_required_tables = berth_count > 0 and capability_count > 0 and history_rows > 0
    has_enough_data = (
        has_required_tables
        and valid_rows >= MIN_VALID_TRAINING_ROWS
        and berth_class_count >= MIN_BERTH_CLASSES
    )
    trained = not missing_models and not stale_models

    if not has_required_tables:
        status = DATA_MISSING
        message = "Data Missing"
    elif not has_enough_data:
        status = INSUFFICIENT_DATA
        message = (
            "Insufficient Data: needs at least "
            f"{MIN_VALID_TRAINING_ROWS} valid rows across {MIN_BERTH_CLASSES} berths."
        )
    elif trained:
        status = TRAINED
        message = "Trained"
    else:
        status = TRAINING_PENDING
        message = "Data Loaded - Training Pending"

    runtime_status = get_training_status_snapshot(normalized_port_code)
    if runtime_status and runtime_status.get("training_status") in {
        TRAINING_IN_PROGRESS.code,
        TRAINING_FAILED.code,
    }:
        status_code = runtime_status["training_status"]
        status_label = runtime_status["status_label"]
        message = runtime_status["training_message"]
    else:
        status_code = status.code
        status_label = status.label

    return {
        "training_status": status_code,
        "status_label": status_label,
        "training_message": message,
        "trained": trained,
        "has_enough_data": has_enough_data,
        "is_stale": bool(stale_models),
        "models_required": list(REQUIRED_MODELS),
        "models_active": active_names,
        "models_missing": missing_models,
        "models_stale": stale_models,
        "history_rows": history_rows,
        "valid_training_rows": valid_rows,
        "berth_count": berth_count,
        "capability_count": capability_count,
        "berth_class_count": berth_class_count,
        "latest_data_ts": latest_data_ts.isoformat() if latest_data_ts else None,
        "data_start_ts": data_start_ts.isoformat() if data_start_ts else None,
        "data_end_ts": data_end_ts.isoformat() if data_end_ts else None,
    }


async def _train_and_register_port(db: AsyncSession, port: BaosPort, *, force: bool = False) -> None:
    port_code = port.port_code
    port_id = port.port_id
    status = await evaluate_port_training_status(db, port_code)
    if not status["has_enough_data"]:
        status_value = DATA_MISSING if status["training_status"] == DATA_MISSING.code else INSUFFICIENT_DATA
        _set_runtime_status(port_code, status_value, status["training_message"], **status)
        logger.info("Skipping ML training for %s: %s", port_code, status["training_message"])
        return

    if status["trained"] and not force:
        _set_runtime_status(port_code, TRAINED, "Trained", **status)
        logger.info("Active ML models for %s are current", port_code)
        return

    _set_runtime_status(port_code, TRAINING_IN_PROGRESS, "Training In Progress", **status)
    logger.info("Training ML models for %s", port_code)

    training_start = _utcnow()
    try:
        df_history = await load_history_from_db(db, port_code)
        port_config = await load_port_config_from_db(db, port_code)
        metadata = await asyncio.to_thread(
            _train_port_models_from_data,
            port_code,
            df_history,
            port_config,
        )
        training_end = _utcnow()
        version = metadata.get("version") or training_end.strftime("%Y%m%d_%H%M%S")
        feature_columns = metadata.get("feature_columns", [])
        feature_schema = {
            "features": feature_columns,
            "feature_count": len(feature_columns),
            "feature_hash": metadata.get("feature_hash"),
        }
        models_dir = Path("ports") / port_code.lower() / "models"
        training_run_version = int(training_end.timestamp())

        for model_name, config in REQUIRED_MODELS.items():
            metrics = metadata.get("results", {}).get(config["metadata_key"], {})
            await register_model(
                db=db,
                port_id=port_id,
                model_name=model_name,
                model_type=config["model_type"],
                target_name=config["target_name"],
                model_version=version,
                artifact_path=str(models_dir / config["artifact_file"]),
                feature_schema=feature_schema,
                metrics=metrics,
                training_rows=int(metadata.get("training_samples", 0) or 0),
                validation_rows=int(metadata.get("validation_samples", 0) or 0),
                test_rows=0,
                split_strategy="train_val_80_20",
                training_start_ts=training_start,
                training_end_ts=training_end,
                data_start_ts=datetime.fromisoformat(status["data_start_ts"]) if status.get("data_start_ts") else None,
                data_end_ts=datetime.fromisoformat(status["data_end_ts"]) if status.get("data_end_ts") else None,
            )
            # FIX (Phase 5): Persist training history with train/validation scores and the feature hash.
            db.add(TrainingRun(
                model_name=model_name,
                version=training_run_version,
                trained_at=training_end,
                train_score=_primary_score(metrics, config["model_type"], "train"),
                val_score=_primary_score(metrics, config["model_type"], "val"),
                data_rows=int(metadata.get("total_samples", 0) or 0),
                feature_hash=metadata.get("feature_hash"),
                hyperparameters=metadata.get("hyperparameters") or settings.training_hyperparameters,
                status="completed",
            ))

        await db.commit()
        final_status = await evaluate_port_training_status(db, port_code)
        _set_runtime_status(port_code, TRAINED, "Trained", **final_status)
        logger.info("Registered ML models for %s version %s", port_code, version)
    except Exception as exc:
        await db.rollback()
        failure_time = _utcnow()
        for model_name in REQUIRED_MODELS:
            # FIX (Phase 5): Failed training attempts are visible in the training history endpoint.
            db.add(TrainingRun(
                model_name=model_name,
                version=int(failure_time.timestamp()),
                trained_at=failure_time,
                data_rows=0,
                hyperparameters=settings.training_hyperparameters,
                status="failed",
                error_message=str(exc),
            ))
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Failed to persist training failure rows for %s", port_code)
        failed_status = await evaluate_port_training_status(db, port_code)
        _set_runtime_status(
            port_code,
            TRAINING_FAILED,
            "Data Loaded, Training Failed",
            error=str(exc),
            **failed_status,
        )
        logger.exception("ML training failed for %s", port_code)


async def auto_train_required_models(
    port_codes: list[str] | None = None,
    *,
    raise_on_busy: bool = False,
    force: bool = False,
) -> None:
    """Entry point used by FastAPI startup."""
    global _training_in_progress
    if _training_in_progress:
        if raise_on_busy:
            raise TrainingAlreadyInProgressError("Training is already in progress. Please wait for it to complete.")
        logger.warning("Training is already in progress; skipping duplicate request")
        return
    if _training_lock.locked():
        if raise_on_busy:
            raise TrainingAlreadyInProgressError("Training lock is held.")
        logger.warning("Training lock is held; skipping duplicate request")
        return

    async with _training_lock:
        _training_in_progress = True
        try:
            async with async_session_factory() as db:
                try:
                    if port_codes:
                        ports = []
                        for port_code in port_codes:
                            port = await get_port_by_code(db, port_code.strip().upper())
                            if port is not None:
                                ports.append(port)
                    else:
                        ports = await list_ports(db, active_only=True)

                    for port in ports:
                        await _train_and_register_port(db, port, force=force)
                except Exception:
                    await db.rollback()
                    logger.exception("Startup ML model check failed")
        finally:
            _training_in_progress = False
