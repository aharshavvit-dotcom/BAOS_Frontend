"""
Optimization Repository — CRUD for baos.optimization_run & assignments.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.baos_models import BaosOptimizationRun, BaosOptimizationAssignment


async def save_optimization_run(
    db: AsyncSession,
    port_id: UUID,
    scenario_name: str = "",
    solver_status: str = "",
    objective_value: float = 0.0,
    total_wait_hours: float = 0.0,
    total_cost_usd: float = 0.0,
    assigned_count: int = 0,
    unassigned_count: int = 0,
    config: dict = None,
    assumptions_used: dict = None,
    request_payload: dict = None,
    result_summary: dict = None,
) -> BaosOptimizationRun:
    """Save an optimization run to the database."""
    run = BaosOptimizationRun(
        port_id=port_id,
        scenario_name=scenario_name,
        solver_status=solver_status,
        objective_value=objective_value,
        total_wait_hours=total_wait_hours,
        total_cost_usd=total_cost_usd,
        assigned_count=assigned_count,
        unassigned_count=unassigned_count,
        config=config or {},
        assumptions_used=assumptions_used or {},
        request_payload=request_payload or {},
        result_summary=result_summary or {},
    )
    db.add(run)
    await db.flush()
    return run


async def save_assignment(
    db: AsyncSession,
    optimization_run_id: UUID,
    vessel_temp_id: str,
    vessel_name: str = "",
    berth_code: str = "",
    assigned: bool = True,
    wait_hours: float = 0.0,
    service_hours: float = 0.0,
    cost_usd: float = 0.0,
    confidence_score: float = 0.0,
    explanation: dict = None,
) -> BaosOptimizationAssignment:
    """Save a single optimization assignment."""
    a = BaosOptimizationAssignment(
        optimization_run_id=optimization_run_id,
        vessel_temp_id=vessel_temp_id,
        vessel_name=vessel_name,
        berth_code=berth_code,
        assigned=assigned,
        wait_hours=wait_hours,
        service_hours=service_hours,
        cost_usd=cost_usd,
        confidence_score=confidence_score,
        explanation=explanation or {},
    )
    db.add(a)
    await db.flush()
    return a


async def get_recent_runs(
    db: AsyncSession,
    port_code: str,
    limit: int = 20,
) -> List[BaosOptimizationRun]:
    """Get recent optimization runs for a port."""
    from database.baos_models import BaosPort
    result = await db.execute(
        select(BaosOptimizationRun)
        .join(BaosPort, BaosOptimizationRun.port_id == BaosPort.port_id)
        .where(BaosPort.port_code == port_code)
        .options(selectinload(BaosOptimizationRun.assignments))
        .order_by(BaosOptimizationRun.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().unique().all())
