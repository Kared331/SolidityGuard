from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FuzzingResult, Project
from app.state.project_state import ProjectStatus
from app.services.task_dispatcher import get_task_dispatcher, TaskAlreadyRunning
from app.tasks.pipeline import build_fuzz_pipeline  # 保留：E2 技术冗余

from fastapi import HTTPException


async def trigger_fuzz(db: AsyncSession, project_id: int) -> str:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for fuzzing")
    # P1-1: 统一走 dispatcher（含幂等检查）
    dispatcher = get_task_dispatcher()
    try:
        return dispatcher.dispatch_fuzz(project_id)
    except TaskAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e))


async def list_fuzz_results(db: AsyncSession, project_id: int) -> list[FuzzingResult]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(FuzzingResult)
        .where(FuzzingResult.project_id == project_id)
        .order_by(FuzzingResult.created_at.desc())
    )
    return list(result.scalars().all())
