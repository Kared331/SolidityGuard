from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditRun, LLMAuditResult, Project
from app.services.task_dispatcher import TaskAlreadyRunning, _apply_with_connection, get_task_dispatcher
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


async def trigger_incremental_audit(
    db: AsyncSession,
    project_id: int,
    diff_text: str,
    path_map: dict[str, str] | None = None,
) -> str:
    """Dispatch an audit that only covers functions touched by `diff_text`."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for LLM audit")

    from app.tasks.run_incremental_audit import run_incremental_audit

    result = _apply_with_connection(
        lambda conn: run_incremental_audit.apply_async(
            kwargs={"project_id": project_id, "diff_text": diff_text, "path_map": path_map},
            connection=conn,
        )
    )
    return result.id


async def compare_audit_runs(db: AsyncSession, base_run_id: int, head_run_id: int) -> dict:
    """Diff the findings of two runs of the same project."""
    base = await db.get(AuditRun, base_run_id)
    head = await db.get(AuditRun, head_run_id)
    if base is None or head is None:
        raise HTTPException(status_code=404, detail="Audit run not found")
    if base.project_id != head.project_id:
        raise HTTPException(status_code=400, detail="Runs belong to different projects")

    rows = (
        (await db.execute(select(LLMAuditResult).where(LLMAuditResult.audit_run_id.in_([base_run_id, head_run_id]))))
        .scalars()
        .all()
    )

    def key(row: LLMAuditResult) -> tuple:
        return (row.contract_name, row.function_name or "", row.severity)

    base_keys = {key(r) for r in rows if r.audit_run_id == base_run_id}
    head_keys = {key(r) for r in rows if r.audit_run_id == head_run_id}

    def as_list(keys: set[tuple]) -> list[dict]:
        return [{"contract": c, "function": f, "severity": s} for c, f, s in sorted(keys)]

    return {
        "base": {
            "run_id": base.id,
            "status": base.status,
            "functions_audited": base.functions_audited,
            "findings": len(base_keys),
        },
        "head": {
            "run_id": head.id,
            "status": head.status,
            "functions_audited": head.functions_audited,
            "findings": len(head_keys),
        },
        "added": as_list(head_keys - base_keys),
        "removed": as_list(base_keys - head_keys),
        "persisted": as_list(base_keys & head_keys),
        "counts": {
            "added": len(head_keys - base_keys),
            "removed": len(base_keys - head_keys),
            "persisted": len(base_keys & head_keys),
        },
    }


async def list_llm_audit_results(db: AsyncSession, project_id: int) -> list[LLMAuditResult]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(LLMAuditResult).where(LLMAuditResult.project_id == project_id))
    return list(result.scalars().all())
