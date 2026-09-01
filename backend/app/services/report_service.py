from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Report
from app.services.infra.storage import REPORT_DIR
from app.state.project_state import ProjectStatus
from app.services.task_dispatcher import get_task_dispatcher, TaskAlreadyRunning
from app.tasks.pipeline import build_report_pipeline  # 保留：E2 技术冗余

from fastapi import HTTPException


async def trigger_report(db: AsyncSession, project_id: int, fmt: str) -> str:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for report generation")
    output_format = fmt.lower()
    if output_format not in ("html", "pdf", "word"):
        raise HTTPException(status_code=400, detail="format must be html, pdf, or word")
    # P1-1: 统一走 dispatcher（含幂等检查）
    dispatcher = get_task_dispatcher()
    try:
        return dispatcher.dispatch_report(project_id, output_format)
    except TaskAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e))


async def list_reports(db: AsyncSession, project_id: int) -> list[Report]:
    result = await db.execute(
        select(Report)
        .where(Report.project_id == project_id)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_report_download_info(db: AsyncSession, report_id: int, fmt: str) -> tuple[str, str, str]:
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    file_paths = report.file_paths or {}
    file_path = file_paths.get(fmt)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Report not available in '{fmt}' format",
        )

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    # Path traversal protection: ensure file is within reports directory
    resolved_path = Path(file_path).resolve()
    reports_base = Path(REPORT_DIR).resolve()
    try:
        resolved_path.relative_to(reports_base)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

    media_types = {
        "html": "text/html",
        "pdf": "application/pdf",
        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(fmt, "application/octet-stream")
    filename = os.path.basename(file_path)

    return file_path, media_type, filename
