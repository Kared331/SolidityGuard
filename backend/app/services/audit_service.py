from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LLMAuditResult, Project
from app.services.task_dispatcher import TaskAlreadyRunning, get_task_dispatcher
from app.state.project_state import ProjectStatus


async def trigger_llm_audit(db: AsyncSession, project_id: int) -> str:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for LLM audit")
    # P1-1: 统一走 dispatcher（含幂等检查）
    dispatcher = get_task_dispatcher()
    try:
        return dispatcher.dispatch_llm_audit(project_id)
    except TaskAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


async def list_llm_audit_results(db: AsyncSession, project_id: int) -> list[LLMAuditResult]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(LLMAuditResult).where(LLMAuditResult.project_id == project_id))
    return list(result.scalars().all())
