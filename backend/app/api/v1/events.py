"""SSE 事件推送端点。

优先使用 Redis Pub/Sub 实时推送，Redis 不可用时降级为数据库轮询。
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.database import async_session
from app.models import AnalysisResult, FuzzingResult, LLMAuditResult, Project, Report

logger = logging.getLogger("solidguard.api.events")

router = APIRouter()

# 降级轮询配置
POLL_BASE_INTERVAL = 5.0
POLL_MAX_INTERVAL = 30.0
POLL_BACKOFF_MULTIPLIER = 1.5


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


async def _get_counts(project_id: int) -> dict:
    """获取项目各维度计数（独立子查询，避免交叉膨胀）。"""
    async with async_session() as session:
        detections = (
            await session.execute(select(func.count(AnalysisResult.id)).where(AnalysisResult.project_id == project_id))
        ).scalar() or 0

        fuzz = (
            await session.execute(select(func.count(FuzzingResult.id)).where(FuzzingResult.project_id == project_id))
        ).scalar() or 0

        audit = (
            await session.execute(select(func.count(LLMAuditResult.id)).where(LLMAuditResult.project_id == project_id))
        ).scalar() or 0

        reports = (
            await session.execute(select(func.count(Report.id)).where(Report.project_id == project_id))
        ).scalar() or 0

        project = await session.get(Project, project_id)
        status = project.status if project else None

    return {
        "detections": detections,
        "fuzz_results": fuzz,
        "audit_results": audit,
        "reports": reports,
        "status": status,
    }


async def _redis_event_stream(project_id: int, disconnect_event: asyncio.Event) -> AsyncIterator[str]:
    """Redis Pub/Sub 实时事件流（主路径）。"""
    from app.llm.pipeline.stream import get_audit_stream

    stream = get_audit_stream()
    async for event in stream.subscribe(project_id):
        if disconnect_event.is_set():
            break
        yield _sse_event(event)


async def _polling_event_stream(project_id: int, disconnect_event: asyncio.Event) -> AsyncIterator[str]:
    """数据库轮询事件流（降级路径）。"""
    prev = await _get_counts(project_id)
    interval = POLL_BASE_INTERVAL

    while not disconnect_event.is_set():
        try:
            await asyncio.wait_for(disconnect_event.wait(), timeout=interval)
            break
        except TimeoutError:
            pass

        curr = await _get_counts(project_id)
        changed = False

        if curr["status"] != prev["status"]:
            changed = True
            yield _sse_event({"type": "status_change", "status": curr["status"], "project_id": project_id})

        for key, event_type in [
            ("detections", "new_detections"),
            ("fuzz_results", "new_fuzz_results"),
            ("audit_results", "new_audit_results"),
            ("reports", "new_report"),
        ]:
            if curr[key] > prev[key]:
                changed = True
                yield _sse_event({"type": event_type, "count": curr[key], "project_id": project_id})

        interval = POLL_BASE_INTERVAL if changed else min(interval * POLL_BACKOFF_MULTIPLIER, POLL_MAX_INTERVAL)
        prev = curr


@router.get("/projects/{project_id}/events")
async def project_events(project_id: int):
    """SSE 事件端点：优先 Redis Pub/Sub，降级为数据库轮询。"""
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404)

    disconnect_event = asyncio.Event()

    async def on_disconnect():
        disconnect_event.set()

    # 尝试 Redis Pub/Sub，失败则降级为轮询
    use_redis = True
    try:
        from app.llm.pipeline.stream import get_audit_stream

        stream = get_audit_stream()
        if not await stream.health_check():
            raise ConnectionError("Redis health check failed")
    except Exception as e:
        logger.warning("Redis unavailable, falling back to polling: %s", e)
        use_redis = False

    if use_redis:
        generator = _redis_event_stream(project_id, disconnect_event)
    else:
        generator = _polling_event_stream(project_id, disconnect_event)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        background=on_disconnect,
    )
