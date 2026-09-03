from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisResult, Detection, FalsePositiveFeedback, Project
from app.services.task_dispatcher import TaskAlreadyRunning, get_task_dispatcher
from app.state.project_state import ProjectStatus


async def trigger_analysis(db: AsyncSession, project_id: int) -> str:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for analysis")
    # 通过 TaskDispatcher 接口触发任务，Service 层不直接依赖 app.tasks.*
    # P1-1: 幂等检查——同项目已有运行中分析任务时拒绝
    dispatcher = get_task_dispatcher()
    try:
        return dispatcher.dispatch_analysis(project_id)
    except TaskAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


async def list_analyses_filtered(db: AsyncSession, project_id: int) -> list[Detection]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(Detection)
        .join(AnalysisResult, AnalysisResult.id == Detection.analysis_result_id)
        .where(AnalysisResult.project_id == project_id)
    )
    all_detections = result.scalars().all()

    fp_result = await db.execute(
        select(FalsePositiveFeedback.detection_ref).where(FalsePositiveFeedback.project_id == project_id)
    )
    fp_refs = set(fp_result.scalars().all())

    return [d for d in all_detections if d.detection_ref not in fp_refs]
