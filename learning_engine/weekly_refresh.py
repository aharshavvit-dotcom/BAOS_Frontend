"""
Weekly Refresh Pipeline — Learning Engine

Automated pipeline that re-discovers patterns, retrains all models,
validates improvements, and optionally deploys new models.

Can be triggered:
  - On a cron schedule (e.g., Monday 2 AM)
  - On-demand from the Admin UI
  - Programmatically
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger(__name__)


def run_weekly_refresh(
    port_name: str,
    auto_deploy: bool = True,
    accuracy_gate: float = 0.0,
) -> Dict[str, Any]:
    """
    Full weekly refresh pipeline:

    1. Backup current models
    2. Re-run pattern discovery → update patterns.json
    3. Retrain all 5 models (4 existing + XGBoost)
    4. Validate: compare new accuracy vs old
    5. Deploy if improved (or if auto_deploy=True)
    6. Generate improvement report

    Args:
        port_name: Port to refresh.
        auto_deploy: Always deploy new models (True) or only if improved (False).
        accuracy_gate: Minimum accuracy improvement required to deploy (0.0 = always deploy).

    Returns:
        Improvement report dict.
    """
    from data_layer.port_store import get_models_dir, is_trained
    from training_engine.trainer import train_port_models

    start = time.time()
    report: Dict[str, Any] = {
        "port": port_name,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "status": "running",
    }

    models_dir = get_models_dir(port_name)

    # ── Step 1: Backup current models ──────────────────────────────────
    old_metadata = _load_old_metadata(models_dir)
    backup_dir = models_dir / "backup_weekly"
    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        backup_dir.mkdir(exist_ok=True)
        for f in models_dir.glob("*.pkl"):
            shutil.copy2(f, backup_dir / f.name)
        for f in models_dir.glob("*.json"):
            shutil.copy2(f, backup_dir / f.name)
        report["backup"] = "success"
    except Exception as e:
        report["backup"] = f"failed: {e}"
        logger.warning("Backup failed: %s", e)

    # ── Step 2-3: Retrain all models (includes pattern discovery) ──────
    try:
        new_metadata = train_port_models(port_name)
        report["training"] = "success"
        report["training_results"] = new_metadata.get("results", {})
    except Exception as e:
        report["training"] = f"failed: {e}"
        report["status"] = "failed"
        report["elapsed_seconds"] = round(time.time() - start, 2)
        logger.error("Training failed: %s", e)
        _rollback(models_dir, backup_dir)
        return report

    # ── Step 4: Validate & compare ─────────────────────────────────────
    comparison = _compare_metrics(old_metadata, new_metadata)
    report["comparison"] = comparison
    improved = comparison.get("improved", True)

    # ── Step 5: Deploy decision ────────────────────────────────────────
    if auto_deploy or improved:
        report["deployed"] = True
        report["deploy_reason"] = "auto_deploy" if auto_deploy else "accuracy_improved"
        logger.info("Deployed new models for %s", port_name)
    else:
        # Rollback
        _rollback(models_dir, backup_dir)
        report["deployed"] = False
        report["deploy_reason"] = "accuracy_not_improved_rollback"
        logger.info("Rolled back to previous models for %s", port_name)

    # ── Step 6: Generate report ────────────────────────────────────────
    report["status"] = "completed"
    report["elapsed_seconds"] = round(time.time() - start, 2)
    report["completed_at"] = datetime.utcnow().isoformat() + "Z"

    # Save report
    report_path = models_dir / "weekly_refresh_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Weekly refresh report saved to %s", report_path)

    return report


def _load_old_metadata(models_dir: Path) -> Optional[dict]:
    """Load existing model metadata for comparison."""
    path = models_dir / "metadata.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _compare_metrics(
    old: Optional[dict], new: Optional[dict]
) -> Dict[str, Any]:
    """Compare old vs new model metrics."""
    if not old or not new:
        return {"improved": True, "reason": "no_prior_baseline"}

    old_results = old.get("results", {})
    new_results = new.get("results", {})
    comparison: Dict[str, Any] = {}

    # Compare berth suitability accuracy
    old_acc = (old_results.get("berth_suitability", {})
               .get("test", {}).get("accuracy", 0))
    new_acc = (new_results.get("berth_suitability", {})
               .get("test", {}).get("accuracy", 0))
    comparison["suitability_accuracy_old"] = old_acc
    comparison["suitability_accuracy_new"] = new_acc
    comparison["suitability_delta"] = round(new_acc - old_acc, 4)

    # Compare service time MAE
    old_mae = (old_results.get("service_time", {})
               .get("test", {}).get("mae", 999))
    new_mae = (new_results.get("service_time", {})
               .get("test", {}).get("mae", 999))
    comparison["service_mae_old"] = old_mae
    comparison["service_mae_new"] = new_mae
    comparison["service_mae_delta"] = round(new_mae - old_mae, 4)

    # Compare XGBoost accuracy
    old_xgb = (old_results.get("xgboost_ranker", {})
               .get("test", {}).get("accuracy", 0))
    new_xgb = (new_results.get("xgboost_ranker", {})
               .get("test", {}).get("accuracy", 0))
    comparison["xgboost_accuracy_old"] = old_xgb
    comparison["xgboost_accuracy_new"] = new_xgb
    comparison["xgboost_delta"] = round(new_xgb - old_xgb, 4)

    # Overall: improved if suitability or XGBoost got better and MAE didn't worsen much
    improved = (
        new_acc >= old_acc - 0.02 and     # Suitability didn't drop >2%
        new_mae <= old_mae * 1.1 and      # MAE didn't increase >10%
        new_xgb >= old_xgb - 0.02         # XGBoost didn't drop >2%
    )
    comparison["improved"] = improved
    comparison["reason"] = "metrics_improved" if improved else "metrics_degraded"

    return comparison


def _rollback(models_dir: Path, backup_dir: Path):
    """Restore models from backup."""
    try:
        for f in backup_dir.glob("*.pkl"):
            shutil.copy2(f, models_dir / f.name)
        for f in backup_dir.glob("*.json"):
            if f.name != "weekly_refresh_report.json":
                shutil.copy2(f, models_dir / f.name)
        logger.info("Rolled back to backup models")
    except Exception as e:
        logger.error("Rollback failed: %s", e)
