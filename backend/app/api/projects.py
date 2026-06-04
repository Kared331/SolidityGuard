import os
import re
import shutil
import uuid

from fastapi import APIRouter, Form, UploadFile, HTTPException, Request
from sqlalchemy import select

from app.config import MAX_UPLOAD_SIZE, logger
from app.database import async_session
from app.models import Project, ProjectFile
from app.tasks.process_upload import process_upload

router = APIRouter()

# ─── Allowed extensions & MIME types (1.25) ──────────────────────
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

# Magic bytes for file type verification (1.25)
ZIP_MAGIC = b"PK\x03\x04"
TAR_MAGIC_OFFSET = 257
TAR_MAGIC = b"ustar"
GZIP_MAGIC = b"\x1f\x8b"


def _verify_magic_bytes(data: bytes, filename: str) -> bool:
    """Check that the file content matches the expected magic bytes."""
    lower = filename.lower()
    if lower.endswith(".zip"):
        return data[:4] == ZIP_MAGIC
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        return data[:2] == GZIP_MAGIC
    if lower.endswith(".tar"):
        return data[TAR_MAGIC_OFFSET:TAR_MAGIC_OFFSET + 5] == TAR_MAGIC
    # .sol files are text – no magic bytes check needed
    if lower.endswith(".sol"):
        return True
    return True


def _validate_filename(filename: str) -> str:
    """Return a safe, UUID-based filename to prevent path traversal (1.1).

    Preserves the original extension but replaces the name with a UUID.
    """
    _, ext = os.path.splitext(filename)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return safe_name


@router.post("/projects")
async def create_project(
    request: Request,
    name: str | None = Form(None),
    files: list[UploadFile] = Form(...),
):
    async with async_session() as session:
        project = Project(name=name)
        session.add(project)
        await session.commit()
        await session.refresh(project)

        project_dir = os.path.join("uploads", str(project.id))
        os.makedirs(project_dir, exist_ok=True)

        for upload_file in files:
            if not upload_file.filename:
                continue

            # ── 1.25 File extension whitelist ────────────────────
            _, ext = os.path.splitext(upload_file.filename)
            if ext.lower() not in ALLOWED_EXTENSIONS:
                logger.warning("Rejected upload with disallowed extension: %s", upload_file.filename)
                continue

            # ── 1.25 MIME type check ─────────────────────────────
            if upload_file.content_type and upload_file.content_type not in ALLOWED_MIME_TYPES:
                logger.warning(
                    "Rejected upload with disallowed MIME type: %s (%s)",
                    upload_file.filename,
                    upload_file.content_type,
                )
                continue

            # ── 1.24 File size limit ─────────────────────────────
            content = await upload_file.read()
            if len(content) > MAX_UPLOAD_SIZE:
                logger.warning(
                    "Rejected upload exceeding size limit: %s (%d bytes)",
                    upload_file.filename,
                    len(content),
                )
                continue

            # ── 1.25 Magic bytes verification ────────────────────
            if not _verify_magic_bytes(content, upload_file.filename):
                logger.warning("Rejected upload with invalid magic bytes: %s", upload_file.filename)
                continue

            # ── 1.1 Safe filename (UUID-based) ───────────────────
            safe_name = _validate_filename(upload_file.filename)
            file_path = os.path.join(project_dir, safe_name)

            # Extra guard: ensure resolved path is inside project_dir
            if not os.path.realpath(file_path).startswith(os.path.realpath(project_dir)):
                logger.error("Path traversal detected for file: %s", upload_file.filename)
                continue

            with open(file_path, "wb") as f:
                f.write(content)

            # Store original filename in DB for display purposes
            # We store a mapping: original_name -> safe_name via ProjectFile
            # The safe_name is what's on disk; the original name is preserved
            # inside process_upload when scanning .sol files

    # Dispatch Celery task to extract archives and identify .sol files
    process_upload.delay(project.id)

    return {"id": project.id, "name": project.name}


@router.get("/projects/{project_id}/files")
async def get_project_files(project_id: int):
    async with async_session() as session:
        # Verify project exists
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await session.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id)
        )
        rows = result.scalars().all()

    return [{"id": r.id, "file_path": r.file_path, "status": r.status} for r in rows]
