"""
ML Enrichment — Connects trained ML predictions to the optimization pipeline.

Provides `enrich_vessels_with_ml()` which optionally overrides
`VesselInput.service_time_minutes` with ML-predicted berth occupancy.
"""
from __future__ import annotations
import json, logging, sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from optimization_engine.constraint_model import VesselInput, BerthInput
from data_layer.port_store import get_models_dir, is_trained, load_port_config
from training_engine.feature_builder import build_inference_features
from training_engine.ml_models import ServiceTimePredictor

logger = logging.getLogger(__name__)


def enrich_vessels_with_ml(
    vessels: List[VesselInput],
    berths: List[BerthInput],
    port_name: str,
    override_service_time: bool = True,
) -> Dict[str, float]:
    """
    Use trained ServiceTimePredictor to predict berth occupancy hours
    for each vessel, and optionally set `service_time_minutes` on the vessel.

    Args:
        vessels: List of VesselInput to enrich.
        berths: List of BerthInput (used for feature computation).
        port_name: Port name for loading trained models.
        override_service_time: If True, overwrite vessel.service_time_minutes
                               with the ML prediction for the best-fit berth.

    Returns:
        Dict mapping vessel_id -> predicted service hours (for display).
    """
    if not is_trained(port_name):
        logger.debug("Port %s not trained, skipping ML enrichment", port_name)
        return {}

    models_dir = get_models_dir(port_name)
    model_path = models_dir / "service_time.pkl"
    if not model_path.exists():
        logger.debug("No service_time.pkl found at %s", model_path)
        return {}

    try:
        stp = ServiceTimePredictor.load(model_path)
    except Exception as e:
        logger.warning("Failed to load ServiceTimePredictor: %s", e)
        return {}

    # Load port config for feature builder
    try:
        port_config = load_port_config(port_name)
    except Exception:
        return {}

    # Load feature columns for alignment
    feat_cols_path = models_dir / "feature_columns.json"
    train_cols = None
    if feat_cols_path.exists():
        try:
            with open(feat_cols_path) as f:
                train_cols = json.load(f)
        except Exception:
            pass

    berth_info_map = {b.berth_code: _berth_to_dict(b) for b in berths}
    predictions: Dict[str, float] = {}

    for v in vessels:
        vessel_dict = {
            "loa": v.loa_m,
            "draft": v.draft_m,
            "adraft": v.draft_m,
            "beam": v.beam_m,
            "dwt": 0,
            "cargo_tons": v.cargo_tons,
            "vessel_type": v.vessel_type or "",
            "eta": None,  # Will default to now
        }

        # Predict service time for each eligible berth, take the median
        berth_predictions = []
        for bc, bi in berth_info_map.items():
            # Skip berths vessel can't fit
            if v.loa_m > 0 and bi.get("max_loa_m", 999) < v.loa_m:
                continue
            if v.draft_m > 0 and bi.get("max_draft_m", 20) < v.draft_m:
                continue

            try:
                X = build_inference_features(vessel_dict, bi, port_config)
                # Align columns with training
                if train_cols:
                    for col in train_cols:
                        if col not in X.columns:
                            X[col] = 0
                    X = X[train_cols]

                # Use uncertainty prediction when available
                try:
                    quant = stp.predict_with_uncertainty(X)
                    pred_hours = float(quant[0].point)
                except Exception:
                    pred_hours = float(stp.predict(X)[0])
                berth_predictions.append(pred_hours)
            except Exception:
                continue

        if berth_predictions:
            # Use median prediction across eligible berths
            median_hours = sorted(berth_predictions)[len(berth_predictions) // 2]
            predictions[v.vessel_id] = round(median_hours, 1)

            if override_service_time:
                predicted_minutes = int(median_hours * 60)
                # Only override if the vessel has a default/generic service time
                # (don't override specific user-provided values)
                if v.service_time_minutes in (0, 1440):  # 0 or exactly 24h (default)
                    v.service_time_minutes = max(predicted_minutes, 30)
                    logger.info(
                        "ML override: %s service_time -> %d min (%.1fh)",
                        v.vessel_id, v.service_time_minutes, median_hours,
                    )

    return predictions


def _berth_to_dict(b: BerthInput) -> dict:
    """Convert BerthInput to dict for feature builder compatibility."""
    return {
        "berth_code": b.berth_code,
        "berth_name": b.berth_name,
        "max_loa_m": b.max_loa_m,
        "max_draft_m": b.max_draft_m,
        "depth_m": b.depth_m,
        "max_beam_m": b.max_beam_m,
        "allowed_vessel_types": b.allowed_vessel_types,
        "equipment": getattr(b, 'equipment', []),
    }
