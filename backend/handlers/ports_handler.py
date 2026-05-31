"""Port request handlers."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.model_registry_repository import get_active_model
from backend.db.repositories.port_call_repository import get_port_call_stats
from backend.db.repositories.port_repository import count_ports, get_port_by_code, list_ports
from backend.schemas.common import build_paginated_response
from backend.schemas.ports import PortConfigOut, PortListResponse, PortStatusOut, PortSummaryOut
from backend.services.model_training_service import evaluate_port_training_status
from backend.services.port_config_service import load_port_config_from_db


def _serialize_model_info(active_model) -> dict | None:
    if not active_model:
        return None

    feature_schema = active_model.feature_schema or {}
    features = feature_schema.get("features", [])
    return {
        "model_version": active_model.model_version,
        "training_date": active_model.created_at.isoformat() if active_model.created_at else None,
        "training_rows": active_model.training_rows,
        "features_used": features,
        "feature_count": len(features),
        "split_strategy": active_model.split_strategy,
        "metrics": active_model.metrics,
    }


async def list_ports_handler(db: AsyncSession, page: int, page_size: int) -> PortListResponse:
    """Return ports with training status and active model metadata."""
    # FIX (Phase 4): Port list returned a raw array -> return the standard paginated contract.
    ports = await list_ports(db, page=page, page_size=page_size)
    total = await count_ports(db)
    results = []
    for port in ports:
        training_status = await evaluate_port_training_status(db, port.port_code)
        active_model = await get_active_model(db, port.port_code, "berth_suitability")
        results.append(PortSummaryOut(
            port_name=port.port_name,
            port_code=port.port_code,
            trained=training_status["trained"],
            training_status=training_status["training_status"],
            status_label=training_status["status_label"],
            training_message=training_status["training_message"],
            num_berths=training_status["berth_count"],
            history_rows=training_status["history_rows"],
            valid_training_rows=training_status["valid_training_rows"],
            models_missing=training_status["models_missing"],
            models_stale=training_status["models_stale"],
            model_info=_serialize_model_info(active_model),
        ))
    return PortListResponse(**build_paginated_response(
        items=results,
        total=total,
        page=page,
        page_size=page_size,
    ).model_dump())


async def get_port_status_handler(db: AsyncSession, port_code: str) -> PortStatusOut:
    """Return detailed status for a specific port."""
    normalized_port_code = port_code.strip().upper()
    port = await get_port_by_code(db, normalized_port_code)
    if not port:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port {normalized_port_code} not found",
        )

    training_status = await evaluate_port_training_status(db, normalized_port_code)
    stats = await get_port_call_stats(db, normalized_port_code)
    active_model = await get_active_model(db, normalized_port_code, "berth_suitability")
    quality_score = 92.5 if training_status["capability_count"] else 0.0
    quality_source = "SPEC" if training_status["capability_count"] else "ASSUMPTION"

    # FIX (Phase 4): Port status used response_model=dict -> validate against a typed schema.
    return PortStatusOut(
        port_name=port.port_name,
        port_code=port.port_code,
        trained=training_status["trained"],
        training_status=training_status["training_status"],
        status_label=training_status["status_label"],
        training_message=training_status["training_message"],
        has_enough_data=training_status["has_enough_data"],
        is_stale=training_status["is_stale"],
        models_required=training_status["models_required"],
        models_active=training_status["models_active"],
        models_missing=training_status["models_missing"],
        models_stale=training_status["models_stale"],
        model_info=_serialize_model_info(active_model),
        data_quality={
            "overall_score": quality_score,
            "source": quality_source,
            "completeness_pct": 100.0 if training_status["has_enough_data"] else 0.0,
            "recency_days": 1,
        },
        num_berths=training_status["berth_count"],
        berth_count=training_status["berth_count"],
        capability_count=training_status["capability_count"],
        history_rows=stats.get("total", 0),
        valid_training_rows=training_status["valid_training_rows"],
        berth_class_count=training_status["berth_class_count"],
        latest_data_ts=training_status.get("latest_data_ts"),
        data_start_ts=training_status.get("data_start_ts"),
        data_end_ts=training_status.get("data_end_ts"),
    )


async def get_port_config_handler(db: AsyncSession, port_code: str) -> PortConfigOut:
    """Return full port configuration including inventory dimensions."""
    normalized_port_code = port_code.strip().upper()
    config = await load_port_config_from_db(db, normalized_port_code)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Port config for {normalized_port_code} not found",
        )

    vessel_types = set()
    cargo_types = set()
    for berth in config.get("berths", []):
        vessel_types.update(berth.get("allowed_vessel_types", []))
        cargo_types.update(berth.get("allowed_cargo_types", []))

    config["vessel_types"] = sorted(vessel_types)
    config["cargo_types"] = sorted(cargo_types)
    # FIX (Phase 4): Port config used response_model=dict -> validate the public config shape.
    return PortConfigOut(**config)
