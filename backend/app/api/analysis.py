from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.analysis import AnalysisTriggerResponse, DetectionResponse
from app.services.analysis_service import list_analyses_filtered, trigger_analysis

router = APIRouter(tags=["Analysis"])


@router.post(
    "/{project_id}/analyze",
    response_model=AnalysisTriggerResponse,
    summary="触发 Slither 分析",
    description="启动指定项目的 Slither 静态分析任务，返回 Celery 任务 ID。",
)
async def analyze_project(project_id: int, db: AsyncSession = Depends(get_db)):
    task_id = await trigger_analysis(db, project_id)
    return AnalysisTriggerResponse(status="started", project_id=project_id, task_id=task_id)


@router.get(
    "/{project_id}/analyses",
    response_model=list[DetectionResponse],
    summary="获取分析结果",
    description="返回指定项目的所有 Slither 检测结果。",
)
async def list_analyses(project_id: int, db: AsyncSession = Depends(get_db)):
    filtered = await list_analyses_filtered(db, project_id)
    return [
        DetectionResponse(
            id=d.id,
            analysis_result_id=d.analysis_result_id,
            detection_ref=d.detection_ref,
            check_name=d.check_name,
            description=d.description,
            impact=d.impact,
            confidence=d.confidence,
        )
        for d in filtered
    ]
