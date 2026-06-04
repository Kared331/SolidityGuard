from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.database import async_session
from app.models import VulnerabilityEntry

router = APIRouter()


@router.get("/vulnerabilities")
async def list_vulnerabilities(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    async with async_session() as session:
        query = select(VulnerabilityEntry)
        count_query = select(func.count(VulnerabilityEntry.id))

        if search:
            like = f"%{search}%"
            from sqlalchemy import or_

            filter_clause = or_(
                VulnerabilityEntry.title.ilike(like),
                VulnerabilityEntry.description.ilike(like),
            )
            query = query.where(filter_clause)
            count_query = count_query.where(filter_clause)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(VulnerabilityEntry.swc_id)
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
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
