from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VulnerabilityEntry
from app.services.task_dispatcher import _apply_with_connection


def trigger_swc_sync() -> None:
    """发布 SWC 同步任务（显式连接，绕 producer pool hostname 丢失）。"""
    from app.tasks.sync_swc import sync_swc

    _apply_with_connection(
        lambda conn: sync_swc.apply_async(connection=conn)
    )


async def search_vulnerabilities(
    db: AsyncSession,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = select(VulnerabilityEntry)
    count_query = select(func.count(VulnerabilityEntry.id))

    if search:
        like = f"%{search}%"
        filter_clause = or_(
            VulnerabilityEntry.title.ilike(like),
            VulnerabilityEntry.description.ilike(like),
        )
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(VulnerabilityEntry.swc_id)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "swc_id": r.swc_id,
                "title": r.title,
                "description": r.description,
                "severity": r.severity,
                "code_example": r.code_example,
            }
            for r in rows
        ],
    }
