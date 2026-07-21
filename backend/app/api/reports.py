from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.report import ReportCreateRequest, ReportTriggerResponse, ReportListItemResponse
from app.services.report_service import trigger_report, list_reports, get_report_download_info

router = APIRouter()


@router.post("/projects/{project_id}/report", response_model=ReportTriggerResponse)
async def create_report(
    project_id: int,
    body: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    task_id = await trigger_report(db, project_id, body.format)
    return ReportTriggerResponse(
        status="report_started",
        project_id=project_id,
        format=body.format.lower(),
        task_id=task_id,
    )


@router.get("/projects/{project_id}/reports", response_model=list[ReportListItemResponse])
async def list_project_reports(project_id: int, db: AsyncSession = Depends(get_db)):
    reports = await list_reports(db, project_id)
    return [
        ReportListItemResponse(
            id=r.id,
            title=r.title,
            file_paths=r.file_paths,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/reports/{report_id}/download")
async def download_report(report_id: int, format: str = "html", db: AsyncSession = Depends(get_db)):
    file_path, media_type, filename = await get_report_download_info(db, report_id, format)
    return FileResponse(path=file_path, media_type=media_type, filename=filename)
