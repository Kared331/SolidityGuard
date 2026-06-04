from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.models import FuzzingResult, Project
from app.tasks.run_fuzzer import run_fuzzer

router = APIRouter()


@router.post("/{project_id}/fuzz")
async def start_fuzz(project_id: int):
    async with async_session() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

    run_fuzzer.delay(project_id)
    return {"status": "fuzz_started", "project_id": project_id}


@router.get("/{project_id}/fuzz-results")
async def get_fuzz_results(project_id: int):
    async with async_session() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await session.execute(
            select(FuzzingResult)
            .where(FuzzingResult.project_id == project_id)
            .order_by(FuzzingResult.created_at.desc())
        )
        rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "failures_count": len(r.failures_json) if r.failures_json else 0,
            "raw_output": r.raw_output[:500],
        }
        for r in rows
    ]
