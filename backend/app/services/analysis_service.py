from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisResult, Detection, FalsePositiveFeedback, Project
from app.state.project_state import ProjectStatus
from app.tasks.pipeline import build_analysis_pipeline

from fastapi import HTTPException


async def trigger_analysis(db: AsyncSession, project_id: int) -> str:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for analysis")
    result = build_analysis_pipeline(project_id).apply_async()
    return result.id


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
        select(FalsePositiveFeedback.detection_ref)
        .where(FalsePositiveFeedback.project_id == project_id)
    )
    fp_refs = set(fp_result.scalars().all())

    return [d for d in all_detections if d.detection_ref not in fp_refs]
