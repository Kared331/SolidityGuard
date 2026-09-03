from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.knowledge import VulnerabilityItemResponse, VulnerabilityPaginatedResponse
from app.services.knowledge_service import search_vulnerabilities

router = APIRouter(tags=["Vulnerabilities"])


@router.get(
    "/vulnerabilities",
    response_model=VulnerabilityPaginatedResponse,
    summary="搜索漏洞知识库",
    description="分页搜索 SWC 漏洞知识库，支持关键词过滤。",
)
async def list_vulnerabilities(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    data = await search_vulnerabilities(db, search, page, page_size)
    return VulnerabilityPaginatedResponse(
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        items=[VulnerabilityItemResponse(**item) for item in data["items"]],
    )
