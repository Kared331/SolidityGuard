from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.fuzz import FuzzTriggerResponse, FuzzResultResponse
from app.services.fuzz_service import trigger_fuzz, list_fuzz_results

router = APIRouter()


@router.post("/{project_id}/fuzz", response_model=FuzzTriggerResponse)
async def start_fuzz(project_id: int, db: AsyncSession = Depends(get_db)):
    task_id = await trigger_fuzz(db, project_id)
    return FuzzTriggerResponse(status="fuzz_started", project_id=project_id, task_id=task_id)


@router.get("/{project_id}/fuzz-results", response_model=list[FuzzResultResponse])
async def get_fuzz_results(project_id: int, db: AsyncSession = Depends(get_db)):
    rows = await list_fuzz_results(db, project_id)
    return [
        FuzzResultResponse(
            id=r.id,
            created_at=r.created_at,
            failures_count=len(r.failures_json) if r.failures_json else 0,
            raw_output=r.raw_output[:500],
        )
        for r in rows
    ]
