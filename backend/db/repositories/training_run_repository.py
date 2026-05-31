"""Training run repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.baos_models import TrainingRun


async def list_training_runs(db: AsyncSession, limit: int = 20) -> list[TrainingRun]:
    """Return the latest training run records."""
    # FIX (Phase 5): Phase checkpoint needs a durable training history endpoint.
    result = await db.execute(
        select(TrainingRun)
        .order_by(TrainingRun.trained_at.desc(), TrainingRun.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
