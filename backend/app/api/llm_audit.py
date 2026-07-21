from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.audit import AuditTriggerResponse, LLMAuditResultResponse
from app.services.audit_service import trigger_llm_audit, list_llm_audit_results

router = APIRouter()


@router.post("/{project_id}/llm-audit", response_model=AuditTriggerResponse)
async def start_llm_audit(project_id: int, db: AsyncSession = Depends(get_db)):
    task_id = await trigger_llm_audit(db, project_id)
    return AuditTriggerResponse(status="audit_started", project_id=project_id, task_id=task_id)


@router.get("/{project_id}/llm-audit-results", response_model=list[LLMAuditResultResponse])
async def get_llm_audit_results(project_id: int, db: AsyncSession = Depends(get_db)):
    rows = await list_llm_audit_results(db, project_id)
    return [
        LLMAuditResultResponse(
            id=r.id,
            contract_name=r.contract_name,
            function_name=r.function_name,
            vulnerability_description=r.vulnerability_description,
            severity=r.severity,
            suggested_fix=r.suggested_fix,
            gas_optimization=r.gas_optimization,
            created_at=r.created_at,
        )
        for r in rows
    ]
