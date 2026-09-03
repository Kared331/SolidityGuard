from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.project import ProjectFileResponse, ProjectResponse
from app.services.project_service import (
    create_project_with_files,
    get_all_projects,
    get_project_files,
    get_project_or_404,
)
from app.state.project_state import ProjectStatus, get_available_actions

router = APIRouter(tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    summary="创建项目",
    description="上传 Solidity 合约文件（.sol）或压缩包（.zip/.tar.gz）创建新项目。支持 Magic Bytes 校验和路径遍历防护。",
)
async def create_project(
    name: str | None = Form(None, description="项目名称（可选）"),
    files: list[UploadFile] = File(..., description="合约文件或压缩包"),
    db: AsyncSession = Depends(get_db),
):
    project = await create_project_with_files(db, name, files)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        available_actions=get_available_actions(ProjectStatus(project.status)),
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="获取项目列表",
    description="返回所有项目，按创建时间倒序排列。",
)
async def list_projects(
    db: AsyncSession = Depends(get_db),
):
    projects = await get_all_projects(db)
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            status=p.status,
            created_at=p.created_at,
            available_actions=get_available_actions(ProjectStatus(p.status)),
        )
        for p in projects
    ]


@router.get(
    "/{project_id}/files",
    response_model=list[ProjectFileResponse],
    summary="获取项目文件列表",
    description="返回指定项目下的所有文件及其处理状态。",
)
async def list_project_files(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    rows = await get_project_files(db, project_id)
    return [ProjectFileResponse(id=r.id, file_path=r.file_path, status=r.status) for r in rows]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="获取项目详情",
    description="返回指定项目的详细信息，包括状态和可用操作。",
)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_or_404(db, project_id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        available_actions=get_available_actions(ProjectStatus(project.status)),
    )
