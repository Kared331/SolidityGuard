from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.models import LLMAuditResult, Project
from app.tasks.run_llm_audit import run_llm_audit

router = APIRouter()


@router.post("/projects/{project_id}/llm-audit")
async def start_llm_audit(project_id: int):
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    run_llm_audit.delay(project_id)
    return {"status": "audit_started", "project_id": project_id}


@router.get("/projects/{project_id}/llm-audit-results")
async def get_llm_audit_results(project_id: int):
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await session.execute(
            select(LLMAuditResult).where(LLMAuditResult.project_id == project_id)
        )
        rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "contract_name": r.contract_name,
            "function_name": r.function_name,
            "vulnerability_description": r.vulnerability_description,
            "severity": r.severity,
            "suggested_fix": r.suggested_fix,
            "gas_optimization": r.gas_optimization,
            "created_at": r.created_at,
        }
        for r in rows
    ]
