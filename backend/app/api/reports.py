"""Reports API – unified async (4.19) with shared session (3.9)."""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.database import async_session
from app.models import Report
from app.tasks.generate_report import generate_report

router = APIRouter()


class ReportRequest(BaseModel):
    format: str = "html"


@router.post("/projects/{project_id}/report")
async def create_report(project_id: int, body: ReportRequest):
    output_format = body.format.lower()
    if output_format not in ("html", "pdf", "word"):
        raise HTTPException(status_code=400, detail="format must be html, pdf, or word")

    generate_report.delay(project_id, output_format)

    return {
        "status": "report_started",
        "project_id": project_id,
        "format": output_format,
    }


@router.get("/projects/{project_id}/reports")
async def list_reports(project_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
        )
        reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "file_paths": r.file_paths,
            "created_at": r.created_at,
        }
        for r in reports
    ]


@router.get("/reports/{report_id}/download")
async def download_report(report_id: int, format: str = "html"):
    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    file_paths = report.file_paths or {}
    file_path = file_paths.get(format)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Report not available in '{format}' format",
        )

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    media_types = {
        "html": "text/html",
        "pdf": "application/pdf",
        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    return FileResponse(
        path=file_path,
        media_type=media_types.get(format, "application/octet-stream"),
        filename=os.path.basename(file_path),
    )
