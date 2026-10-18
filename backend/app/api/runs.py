from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.audit_service import compare_audit_runs

router = APIRouter(tags=["Audit Runs"])


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
