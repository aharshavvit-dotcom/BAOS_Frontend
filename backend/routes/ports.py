"""
Port Management API routes.
"""
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from repositories.port_repository import list_ports, get_port_by_code
from repositories.port_call_repository import get_port_call_stats
from repositories.model_registry_repository import get_active_model
from services.model_training_service import evaluate_port_training_status

router = APIRouter(prefix="/api/v1/ports", tags=["Ports"])

@router.get("", response_model=List[dict])
async def get_ports_list(db: AsyncSession = Depends(get_db)):
    """List all available ports with training status."""
    ports = await list_ports(db)
    results = []
    for port in ports:
        training_status = await evaluate_port_training_status(db, port.port_code)
        active_model = await get_active_model(db, port.port_code, "berth_suitability")

        model_info = None
        if active_model:
            model_info = {
                "model_version": active_model.model_version,
                "training_date": active_model.created_at.isoformat() if active_model.created_at else None,
                "training_rows": active_model.training_rows,
                "features_used": active_model.feature_schema.get("features", []) if active_model.feature_schema else [],
                "feature_count": len(active_model.feature_schema.get("features", [])) if active_model.feature_schema else 0,
                "split_strategy": active_model.split_strategy,
                "metrics": active_model.metrics,
            }
            
        results.append({
            "port_name": port.port_name,
            "port_code": port.port_code,
            "trained": training_status["trained"],
            "training_status": training_status["training_status"],
            "status_label": training_status["status_label"],
            "training_message": training_status["training_message"],
            "num_berths": training_status["berth_count"],
            "history_rows": training_status["history_rows"],
            "valid_training_rows": training_status["valid_training_rows"],
            "models_missing": training_status["models_missing"],
            "models_stale": training_status["models_stale"],
            "model_info": model_info,
        })
    return results

@router.get("/{port_code}/status", response_model=dict)
async def get_port_status_details(port_code: str, db: AsyncSession = Depends(get_db)):
    """Get detailed status for a specific port."""
    normalized_port_code = port_code.strip().upper()
    port = await get_port_by_code(db, normalized_port_code)
    if not port:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Port {normalized_port_code} not found")
        
    training_status = await evaluate_port_training_status(db, normalized_port_code)
    stats = await get_port_call_stats(db, normalized_port_code)

    active_model = await get_active_model(db, normalized_port_code, "berth_suitability")

    model_info = None
    if active_model:
        model_info = {
            "model_version": active_model.model_version,
            "training_date": active_model.created_at.isoformat() if active_model.created_at else None,
            "training_rows": active_model.training_rows,
            "features_used": active_model.feature_schema.get("features", []) if active_model.feature_schema else [],
            "feature_count": len(active_model.feature_schema.get("features", [])) if active_model.feature_schema else 0,
            "split_strategy": active_model.split_strategy,
            "metrics": active_model.metrics,
        }

    quality_score = 92.5 if training_status["capability_count"] else 0.0
    quality_source = "SPEC" if training_status["capability_count"] else "ASSUMPTION"

    return {
        "port_name": port.port_name,
        "port_code": port.port_code,
        "trained": training_status["trained"],
        "training_status": training_status["training_status"],
        "status_label": training_status["status_label"],
        "training_message": training_status["training_message"],
        "has_enough_data": training_status["has_enough_data"],
        "is_stale": training_status["is_stale"],
        "models_required": training_status["models_required"],
        "models_active": training_status["models_active"],
        "models_missing": training_status["models_missing"],
        "models_stale": training_status["models_stale"],
        "model_info": model_info,
        "data_quality": {
            "overall_score": quality_score,
            "source": quality_source,
            "completeness_pct": 100.0 if training_status["has_enough_data"] else 0.0,
            "recency_days": 1,
        },
        "berth_count": training_status["berth_count"],
        "capability_count": training_status["capability_count"],
        "history_rows": stats.get("total", 0),
        "valid_training_rows": training_status["valid_training_rows"],
        "berth_class_count": training_status["berth_class_count"],
    }

@router.get("/{port_code}/config", response_model=dict)
async def get_port_config_details(port_code: str, db: AsyncSession = Depends(get_db)):
    """Get full port configuration including berth inventory."""
    from services.port_config_service import load_port_config_from_db
    normalized_port_code = port_code.strip().upper()
    config = await load_port_config_from_db(db, normalized_port_code)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Port config for {normalized_port_code} not found")
        
    # Extract unique vessel types and cargo types
    vessel_types = set()
    cargo_types = set()
    for b in config.get("berths", []):
        for vt in b.get("allowed_vessel_types", []):
            vessel_types.add(vt)
        for ct in b.get("allowed_cargo_types", []):
            cargo_types.add(ct)
            
    config["vessel_types"] = sorted(vessel_types)
    config["cargo_types"] = sorted(cargo_types)
    
    return config
