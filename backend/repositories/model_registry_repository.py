"""
ML Model Registry Repository — CRUD for baos.ml_model_registry.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.baos_models import BaosMLModelRegistry, BaosPort


async def get_active_model(
    db: AsyncSession,
    port_code: str,
    model_name: str,
) -> Optional[BaosMLModelRegistry]:
    """Get the currently active model for a port + model_name."""
    result = await db.execute(
        select(BaosMLModelRegistry)
        .join(BaosPort, BaosMLModelRegistry.port_id == BaosPort.port_id)
        .where(
            BaosPort.port_code == port_code,
            BaosMLModelRegistry.model_name == model_name,
            BaosMLModelRegistry.is_active == True,  # noqa: E712
        )
        .order_by(BaosMLModelRegistry.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_models(
    db: AsyncSession,
    port_code: str,
) -> List[BaosMLModelRegistry]:
    """List all models for a port."""
    result = await db.execute(
        select(BaosMLModelRegistry)
        .join(BaosPort, BaosMLModelRegistry.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
        .order_by(BaosMLModelRegistry.created_at.desc())
    )
    return list(result.scalars().all())


async def register_model(
    db: AsyncSession,
    port_id: UUID,
    model_name: str,
    model_type: str,
    target_name: str,
    model_version: str,
    artifact_path: str = "",
    feature_schema: dict = None,
    metrics: dict = None,
    training_rows: int = 0,
    validation_rows: int = 0,
    test_rows: int = 0,
    split_strategy: str = "random",
    training_start_ts: datetime | None = None,
    training_end_ts: datetime | None = None,
    data_start_ts: datetime | None = None,
    data_end_ts: datetime | None = None,
    baseline_metrics: dict = None,
) -> BaosMLModelRegistry:
    """Register a newly trained model, deactivating previous versions."""
    # Deactivate previous active versions
    from sqlalchemy import update
    await db.execute(
        update(BaosMLModelRegistry)
        .where(
            BaosMLModelRegistry.port_id == port_id,
            BaosMLModelRegistry.model_name == model_name,
            BaosMLModelRegistry.is_active == True,  # noqa: E712
        )
        .values(is_active=False)
    )

    model = BaosMLModelRegistry(
        port_id=port_id,
        model_name=model_name,
        model_type=model_type,
        target_name=target_name,
        model_version=model_version,
        artifact_path=artifact_path,
        feature_schema=feature_schema or {},
        metrics=metrics or {},
        baseline_metrics=baseline_metrics or {},
        training_start_ts=training_start_ts,
        training_end_ts=training_end_ts,
        training_rows=training_rows,
        validation_rows=validation_rows,
        test_rows=test_rows,
        split_strategy=split_strategy,
        data_start_ts=data_start_ts,
        data_end_ts=data_end_ts,
        is_active=True,
    )
    db.add(model)
    await db.flush()
    return model
