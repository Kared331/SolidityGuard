from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LLMAuditResult, Project
from app.state.project_state import ProjectStatus
from app.tasks.pipeline import build_llm_audit_pipeline

from fastapi import HTTPException


async def trigger_llm_audit(db: AsyncSession, project_id: int) -> str:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for LLM audit")
    result = build_llm_audit_pipeline(project_id).apply_async()
    return result.id


async def list_llm_audit_results(db: AsyncSession, project_id: int) -> list[LLMAuditResult]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(LLMAuditResult).where(LLMAuditResult.project_id == project_id)
    )
    return list(result.scalars().all())
