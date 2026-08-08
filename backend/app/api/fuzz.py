from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.fuzz import FuzzTriggerResponse, FuzzResultResponse
from app.services.fuzz_service import trigger_fuzz, list_fuzz_results

router = APIRouter(tags=["Fuzzing"])


@router.post(
    "/{project_id}/fuzz",
    response_model=FuzzTriggerResponse,
    summary="触发 Fuzzing 测试",
    description="启动指定项目的 Foundry Fuzzing 测试任务。",
)
async def start_fuzz(project_id: int, db: AsyncSession = Depends(get_db)):
    task_id = await trigger_fuzz(db, project_id)
    return FuzzTriggerResponse(status="fuzz_started", project_id=project_id, task_id=task_id)


@router.get(
    "/{project_id}/fuzz-results",
    response_model=list[FuzzResultResponse],
    summary="获取 Fuzzing 结果",
    description="返回指定项目的所有 Fuzzing 测试结果，包含失败数量和原始输出摘要。",
)
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
