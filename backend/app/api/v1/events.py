import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func

from app.database import async_session
from app.models import Project, AnalysisResult, FuzzingResult, LLMAuditResult, Report
from app.config import settings

router = APIRouter()

# SSE polling config
BASE_INTERVAL = 5.0  # Base polling interval in seconds (was 1s)
MAX_INTERVAL = 30.0  # Max interval with backoff
BACKOFF_MULTIPLIER = 1.5  # Multiply interval when no changes


def _sse_event(event_name: str, data: dict) -> str:
    # Use unnamed events so browser EventSource.onmessage catches them.
    # Event type is carried inside the JSON payload as "type".
    return f"data: {json.dumps(data)}\n\n"


async def _get_counts(project_id: int) -> dict:
    """Fetch all counts using independent subqueries to avoid cross-join inflation."""
    async with async_session() as session:
        detections_q = (
            select(func.count(AnalysisResult.id))
            .where(AnalysisResult.project_id == project_id)
        )
        detections = (await session.execute(detections_q)).scalar() or 0

        fuzz_q = (
            select(func.count(FuzzingResult.id))
            .where(FuzzingResult.project_id == project_id)
        )
        fuzz = (await session.execute(fuzz_q)).scalar() or 0

        audit_q = (
            select(func.count(LLMAuditResult.id))
            .where(LLMAuditResult.project_id == project_id)
        )
        audit = (await session.execute(audit_q)).scalar() or 0

        reports_q = (
            select(func.count(Report.id))
            .where(Report.project_id == project_id)
        )
        reports = (await session.execute(reports_q)).scalar() or 0

        project = await session.get(Project, project_id)
        status = project.status if project else None
    return {
        "detections": detections,
        "fuzz_results": fuzz,
        "audit_results": audit,
        "reports": reports,
        "status": status,
    }


async def event_generator(project_id: int, disconnect_event: asyncio.Event):
    """SSE event generator with adaptive polling interval."""
    prev = await _get_counts(project_id)
    interval = BASE_INTERVAL
    while not disconnect_event.is_set():
        try:
            await asyncio.wait_for(disconnect_event.wait(), timeout=interval)
            break  # Client disconnected
        except asyncio.TimeoutError:
            pass  # No disconnect, continue polling

        curr = await _get_counts(project_id)
        changed = False
        if curr["status"] != prev["status"]:
            changed = True
            yield _sse_event(
                "status_change",
                {"type": "status_change", "status": curr["status"], "project_id": project_id},
            )
        if curr["detections"] > prev["detections"]:
            changed = True
            yield _sse_event(
                "new_detections",
                {"type": "new_detections", "count": curr["detections"], "project_id": project_id},
            )
        if curr["fuzz_results"] > prev["fuzz_results"]:
            changed = True
            yield _sse_event(
                "new_fuzz_results",
                {"type": "new_fuzz_results", "count": curr["fuzz_results"], "project_id": project_id},
            )
        if curr["audit_results"] > prev["audit_results"]:
            changed = True
            yield _sse_event(
                "new_audit_results",
                {"type": "new_audit_results", "count": curr["audit_results"], "project_id": project_id},
            )
        if curr["reports"] > prev["reports"]:
            changed = True
            yield _sse_event(
                "new_report",
                {"type": "new_report", "count": curr["reports"], "project_id": project_id},
            )

        # Adaptive backoff: increase interval when no changes, reset on change
        if changed:
            interval = BASE_INTERVAL
        else:
            interval = min(interval * BACKOFF_MULTIPLIER, MAX_INTERVAL)
        prev = curr


@router.get("/projects/{project_id}/events")
async def project_events(project_id: int):
    # Auth handled by router-level verify_api_key dependency
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404)

    disconnect_event = asyncio.Event()

    async def on_disconnect():
        disconnect_event.set()

    return StreamingResponse(
        event_generator(project_id, disconnect_event),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        background=on_disconnect,
    )