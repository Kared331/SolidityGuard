from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from starlette.datastructures import UploadFile
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings, logger
from app.models import Project, ProjectFile
from app.services.infra.storage import get_project_dir
from app.tasks.process_upload import process_upload

ALLOWED_EXTENSIONS = {".sol", ".zip", ".tar", ".gz", ".tgz"}
ALLOWED_MIME_TYPES = {
    "text/plain",
    "application/zip",
    "application/x-zip-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
    "application/octet-stream",
}

ZIP_MAGIC = b"PK\x03\x04"
TAR_MAGIC_OFFSET = 257
TAR_MAGIC = b"ustar"
GZIP_MAGIC = b"\x1f\x8b"


def _verify_magic_bytes(data: bytes, filename: str) -> bool:
    lower = filename.lower()
    if lower.endswith(".zip"):
        if len(data) < 4:
            return False
        return data[:4] == ZIP_MAGIC
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        return data[:2] == GZIP_MAGIC
    if lower.endswith(".tar"):
        return data[TAR_MAGIC_OFFSET:TAR_MAGIC_OFFSET + 5] == TAR_MAGIC
    if lower.endswith(".sol"):
        return True
    return True


def _validate_filename(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return safe_name


async def create_project_with_files(db: AsyncSession, name: str | None, files: list[UploadFile]) -> Project:
    project = Project(name=name)
    db.add(project)
    await db.commit()
    await db.refresh(project)

    project_dir = get_project_dir(project.id)
    os.makedirs(project_dir, exist_ok=True)

    saved_count = 0
    rejected_reasons: list[str] = []

    for upload_file in files:
        if not upload_file.filename:
            rejected_reasons.append(f"file missing filename")
            continue

        _, ext = os.path.splitext(upload_file.filename)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            reason = f"unsupported extension: {ext}"
            logger.warning("Rejected upload %s: %s", upload_file.filename, reason)
            rejected_reasons.append(reason)
            continue

        if upload_file.content_type and upload_file.content_type not in ALLOWED_MIME_TYPES:
            reason = f"unsupported MIME type: {upload_file.content_type}"
            logger.warning("Rejected upload %s: %s", upload_file.filename, reason)
            rejected_reasons.append(reason)
            continue

        if upload_file.size is not None and isinstance(upload_file.size, (int, float)) and upload_file.size > settings.MAX_UPLOAD_SIZE:
            reason = f"file size ({upload_file.size}) exceeds limit ({settings.MAX_UPLOAD_SIZE})"
            logger.warning("Rejected upload %s: %s", upload_file.filename, reason)
            rejected_reasons.append(reason)
            continue

        content = await upload_file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            reason = f"actual content size ({len(content)}) exceeds limit ({settings.MAX_UPLOAD_SIZE})"
            logger.warning("Rejected upload %s: %s", upload_file.filename, reason)
            rejected_reasons.append(reason)
            continue

        if not _verify_magic_bytes(content, upload_file.filename):
            reason = "magic bytes mismatch (file content does not match extension)"
            logger.warning("Rejected upload %s: %s", upload_file.filename, reason)
            rejected_reasons.append(reason)
            continue

        safe_name = _validate_filename(upload_file.filename)
        file_path = os.path.join(project_dir, safe_name)

        if not Path(file_path).resolve().is_relative_to(Path(project_dir).resolve()):
            reason = "path traversal detected"
            logger.error("%s for file: %s", reason, upload_file.filename)
            rejected_reasons.append(reason)
            continue

        with open(file_path, "wb") as f:
            f.write(content)
        saved_count += 1

    if saved_count == 0:
        await db.delete(project)
        await db.commit()
        detail = "以下文件均未通过校验"
        if rejected_reasons:
            detail += ": " + "; ".join(rejected_reasons)
        raise HTTPException(status_code=422, detail=detail)

    process_upload.delay(project.id)
    return project


async def get_all_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


async def get_project_files(db: AsyncSession, project_id: int) -> list[ProjectFile]:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    return list(result.scalars().all())


async def get_project_or_404(db: AsyncSession, project_id: int) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

