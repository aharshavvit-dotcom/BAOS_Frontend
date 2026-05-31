"""Training API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_admin
from backend.db.repositories.training_run_repository import list_training_runs
from backend.db.session import get_db
from backend.services.model_training_service import (
    TrainingAlreadyInProgressError,
    auto_train_required_models,
    get_training_lock_status,
)
from backend.schemas.training import TrainingRunOut, TrainingStartResponse, TrainingStatusResponse

router = APIRouter(prefix="/api/v1/training", tags=["Training"])


@router.post("/start", response_model=TrainingStartResponse)
async def start_training(
    port_code: str | None = None,
    _current_user=Depends(require_admin),
):
    """Start model training for all ports, or one port when provided."""
    try:
        await auto_train_required_models(
            [port_code] if port_code else None,
            raise_on_busy=True,
            # FIX (Phase 5): Manual training start must retrain even when startup found current models.
            force=True,
        )
    except TrainingAlreadyInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # FIX (Phase 4): Training start returned response_model=dict -> validate the status payload.
    return {
        "status": "completed",
        **get_training_lock_status(),
    }


@router.get("/status", response_model=TrainingStatusResponse)
async def training_status(_current_user=Depends(get_current_user)):
    # FIX (Phase 4): Training status returned response_model=dict -> validate lock state.
    return get_training_lock_status()


@router.get("/history", response_model=list[TrainingRunOut])
async def training_history(
    _current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # FIX (Phase 5): Return the latest persisted training runs for checkpoint and audit views.
    return await list_training_runs(db, limit=20)
