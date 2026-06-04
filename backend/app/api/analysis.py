from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.models import AnalysisResult, Detection, FalsePositiveFeedback, Project
from app.tasks.run_slither import run_slither

router = APIRouter()


@router.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: int):
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    run_slither.delay(project_id)
    return {"status": "started", "project_id": project_id}


@router.get("/projects/{project_id}/analyses")
async def list_analyses(project_id: int):
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await session.execute(
            select(Detection)
            .join(AnalysisResult, AnalysisResult.id == Detection.analysis_result_id)
            .where(AnalysisResult.project_id == project_id)
        )
        all_detections = result.scalars().all()

        fp_result = await session.execute(
            select(FalsePositiveFeedback.detection_ref)
        )
        fp_refs = set(fp_result.scalars().all())

        filtered = [
            d for d in all_detections if d.detection_ref not in fp_refs
        ]

    return [
        {
            "id": d.id,
            "analysis_result_id": d.analysis_result_id,
            "detection_ref": d.detection_ref,
            "check_name": d.check_name,
            "description": d.description,
            "impact": d.impact,
            "confidence": d.confidence,
        }
        for d in filtered
    ]
