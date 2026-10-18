from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.audit import AuditRunDetail, AuditRunSummary
from app.services.audit_service import compare_audit_runs, get_audit_run, list_audit_runs

router = APIRouter(tags=["Audit Runs"])


@router.get(
    "/projects/{project_id}/runs",
    response_model=list[AuditRunSummary],
    summary="列出审计运行",
    description="按时间倒序返回项目的审计运行（全量 / 增量），含覆盖率各分项。",
)
async def list_runs(project_id: int, db: AsyncSession = Depends(get_db)):
    return await list_audit_runs(db, project_id)


@router.get(
    "/runs/{run_id}",
    response_model=AuditRunDetail,
    summary="审计运行详情",
    description="返回单次运行的覆盖率、增量计划（changed / unchanged）与逐函数账本。",
)
async def run_detail(run_id: int, db: AsyncSession = Depends(get_db)):
    return await get_audit_run(db, run_id)


@router.get(
    "/runs/{base_run_id}/compare/{head_run_id}",
    summary="对比两次审计结果",
    description="返回新增 / 消失 / 仍然存在的 finding，用于增量审计的变更对比。",
)
async def compare_runs(
    base_run_id: int,
    head_run_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await compare_audit_runs(db, base_run_id, head_run_id)
