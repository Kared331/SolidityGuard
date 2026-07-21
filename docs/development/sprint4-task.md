# Sprint 4: Project State Machine + Task Progress Tracking + Frontend SSE

## Working Directory
D:\MetaGPT_Project\SolidGuard

## Prerequisites (Sprint 1+2+3 completed)
- `backend/app/models/` package with 9 classes (Project has NO status field yet)
- `backend/app/schemas/` package with 9 files
- `backend/app/dependencies.py` with get_db()
- `backend/app/services/` with 7 business service files + engine/ + infra/
- `backend/app/api/` with 8 thin router handlers
- `backend/app/tasks/` with lightweight shells calling Engines
- `backend/app/tasks/pipeline.py` with chain/group orchestration
- `frontend/src/pages/ProjectDetailPage.tsx` with polling logic (3s interval, 20 attempts)
- `frontend/src/pages/ReportPage.tsx` with polling logic

## Goal
1. Add project state machine (3 states: uploaded, processing, ready)
2. Add Alembic migration for status column
3. Add Task Status + SSE endpoints
4. Add status checks in services before triggering tasks
5. Replace frontend polling with SSE + fallback

## PHASE A: State Machine

### Step 1: Create `backend/app/state/__init__.py` (empty)

### Step 2: Create `backend/app/state/project_state.py`
```python
from enum import Enum

class ProjectStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"

VALID_TRANSITIONS = {
    ProjectStatus.UPLOADED: {ProjectStatus.PROCESSING},
    ProjectStatus.PROCESSING: {ProjectStatus.READY},
}

AVAILABLE_ACTIONS = {
    ProjectStatus.UPLOADED: [],
    ProjectStatus.PROCESSING: [],
    ProjectStatus.READY: ["analyze", "fuzz", "llm-audit", "report"],
}

def validate_transition(current: ProjectStatus, target: ProjectStatus) -> bool:
    valid_targets = VALID_TRANSITIONS.get(current, set())
    return target in valid_targets

def get_available_actions(status: ProjectStatus) -> list[str]:
    return AVAILABLE_ACTIONS.get(status, [])
```

### Step 3: Update `backend/app/models/project.py`
Add ONE field to the Project class (do NOT change anything else):
```python
from app.state.project_state import ProjectStatus

# Add this field to Project class:
status: Mapped[str] = mapped_column(
    String(20),
    default=ProjectStatus.UPLOADED.value,
    nullable=False,
)
```

## PHASE B: Alembic Migration

### Step 4: Create `backend/app/alembic/versions/009_add_project_status.py`
```python
"""009 add project status

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        "projects",
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
    )
    op.execute("UPDATE projects SET status = 'ready'")
    op.create_index("ix_projects_status", "projects", ["status"])

def downgrade():
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_column("projects", "status")
```

## PHASE C: Schemas

### Step 5: Update `backend/app/schemas/project.py`
Add two fields to ProjectResponse:
```python
class ProjectResponse(BaseModel):
    id: int
    name: str | None
    status: str = "uploaded"
    available_actions: list[str] = []
```

### Step 6: Create `backend/app/schemas/events.py`
```python
from __future__ import annotations
from pydantic import BaseModel

class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    meta: dict | None = None
```

## PHASE D: New Endpoints

### Step 7: Create `backend/app/api/v1/` directory (if not exists)
Create `backend/app/api/v1/__init__.py` (empty)

### Step 8: Create `backend/app/api/v1/tasks.py`
```python
from fastapi import APIRouter
from app.celery_app import celery

router = APIRouter()

@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    result = celery.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"task_id": task_id, "state": "PENDING", "meta": None}
    if result.state == "PROGRESS":
        return {"task_id": task_id, "state": "PROGRESS", "meta": result.info}
    if result.state == "SUCCESS":
        return {"task_id": task_id, "state": "SUCCESS", "meta": None}
    if result.state == "FAILURE":
        return {"task_id": task_id, "state": "FAILURE", "meta": {"error": str(result.info)}}
    return {"task_id": task_id, "state": result.state, "meta": None}
```

### Step 9: Create `backend/app/api/v1/events.py`
SSE endpoint that polls database every 1 second for changes:
```python
import asyncio
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from app.database import async_session
from app.models import Project, AnalysisResult, FuzzingResult, LLMAuditResult, Report
from app.config import API_KEY

router = APIRouter()

def _sse_event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"

async def _get_counts(project_id: int) -> dict:
    async with async_session() as session:
        detections = await session.scalar(select(func.count(AnalysisResult.id)).where(AnalysisResult.project_id == project_id))
        fuzz = await session.scalar(select(func.count(FuzzingResult.id)).where(FuzzingResult.project_id == project_id))
        audit = await session.scalar(select(func.count(LLMAuditResult.id)).where(LLMAuditResult.project_id == project_id))
        reports = await session.scalar(select(func.count(Report.id)).where(Report.project_id == project_id))
        project = await session.get(Project, project_id)
        status = project.status if project else None
    return {"detections": detections or 0, "fuzz_results": fuzz or 0, "audit_results": audit or 0, "reports": reports or 0, "status": status}

async def event_generator(project_id: int):
    prev = await _get_counts(project_id)
    while True:
        await asyncio.sleep(1)
        curr = await _get_counts(project_id)
        if curr["status"] != prev["status"]:
            yield _sse_event("status_change", {"type": "status_change", "status": curr["status"], "project_id": project_id})
        if curr["detections"] > prev["detections"]:
            yield _sse_event("new_detections", {"type": "new_detections", "count": curr["detections"], "project_id": project_id})
        if curr["fuzz_results"] > prev["fuzz_results"]:
            yield _sse_event("new_fuzz_results", {"type": "new_fuzz_results", "count": curr["fuzz_results"], "project_id": project_id})
        if curr["audit_results"] > prev["audit_results"]:
            yield _sse_event("new_audit_results", {"type": "new_audit_results", "count": curr["audit_results"], "project_id": project_id})
        if curr["reports"] > prev["reports"]:
            yield _sse_event("new_report", {"type": "new_report", "count": curr["reports"], "project_id": project_id})
        prev = curr

@router.get("/projects/{project_id}/events")
async def project_events(project_id: int, api_key: str | None = Query(None)):
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=403)
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404)
    return StreamingResponse(
        event_generator(project_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
```

### Step 10: Update `backend/app/api/router.py`
Add imports and register new routes. The key changes:
```python
from app.api.v1.tasks import router as tasks_router
from app.api.v1.events import router as events_router

# Add after existing router registrations:
api_router.include_router(tasks_router, prefix="/api/v1", dependencies=[Depends(verify_api_key)])
api_router.include_router(events_router, prefix="/api/v1")
# Note: events_router does NOT use verify_api_key (API key passed via query param)
```

## PHASE E: Update Services with Status Checks

### Step 11: Add `update_project_status` to `services/project_service.py`
```python
from app.state.project_state import ProjectStatus, validate_transition

def update_project_status_sync(session, project_id: int, new_status: ProjectStatus) -> None:
    """Synchronous version for Celery tasks."""
    project = session.get(Project, project_id)
    if project:
        current = ProjectStatus(project.status)
        if validate_transition(current, new_status):
            project.status = new_status.value
            session.commit()
```

### Step 12: Update `services/analysis_service.py`
Add status check before triggering:
```python
from app.state.project_state import ProjectStatus

async def trigger_analysis(db, project_id):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != ProjectStatus.READY.value:
        raise HTTPException(status_code=409, detail=f"Project is '{project.status}', not ready for analysis")
    result = build_analysis_pipeline(project_id).apply_async()
    return result.id
```

### Step 13: Same pattern for `fuzz_service.py`, `audit_service.py`, `report_service.py`
Each gets the same status check: `if project.status != ProjectStatus.READY.value: raise 409`

## PHASE F: Update process_upload Task

### Step 14: Update `tasks/process_upload.py`
Add status transitions at start and end:
```python
from app.state.project_state import ProjectStatus
from app.services.project_service import update_project_status_sync

@celery.task(name="process_upload", bind=True)
def process_upload(self, project_id: int) -> None:
    project_dir = get_project_dir(project_id)
    
    # Status: uploaded -> processing
    with get_sync_session() as session:
        update_project_status_sync(session, project_id, ProjectStatus.PROCESSING)
    
    try:
        # ... existing engine call + DB write logic ...
        
        # Status: processing -> ready
        with get_sync_session() as session:
            update_project_status_sync(session, project_id, ProjectStatus.READY)
    except Exception:
        # Keep processing status on failure
        logger.exception("Failed to process upload for project %d", project_id)
        raise
```

## PHASE G: Update API Handlers

### Step 15: Update `api/projects.py` create_project
Return status and available_actions:
```python
from app.state.project_state import get_available_actions, ProjectStatus

@router.post("/projects", response_model=ProjectResponse)
async def create_project(...):
    project = await create_project_with_files(db, name, files)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        available_actions=get_available_actions(ProjectStatus(project.status)),
    )
```

### Step 16: Update analysis/fuzz/audit/report handlers to return task_id
Each trigger endpoint should return task_id in response:
```python
@router.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: int, db: AsyncSession = Depends(get_db)):
    task_id = await trigger_analysis(db, project_id)
    return {"status": "started", "project_id": project_id, "task_id": task_id}
```

## PHASE H: Frontend Changes

### Step 17: Create `frontend/src/hooks/useTaskProgress.ts`
```typescript
import { useState, useEffect, useRef } from 'react';

interface SSEEvent {
    type: string;
    project_id: number;
    [key: string]: unknown;
}

interface UseTaskProgressOptions {
    projectId: string;
    onEvent?: (event: SSEEvent) => void;
    enabled?: boolean;
}

interface UseTaskProgressResult {
    connected: boolean;
    lastEvent: SSEEvent | null;
    error: string | null;
}

function useTaskProgress({ projectId, onEvent, enabled = true }: UseTaskProgressOptions): UseTaskProgressResult {
    const [connected, setConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
    const [error, setError] = useState<string | null>(null);
    const onEventRef = useRef(onEvent);
    onEventRef.current = onEvent;

    useEffect(() => {
        if (!enabled || !projectId) return;
        const apiKey = import.meta.env.VITE_API_KEY || '';
        const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
        let sseUrl = `${baseUrl}/v1/projects/${projectId}/events`;
        if (apiKey) sseUrl += `?api_key=${enco…)}`;

        const es = new EventSource(sseUrl);
        es.onopen = () => { setConnected(true); setError(null); };
        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as SSEEvent;
                setLastEvent(data);
                onEventRef.current?.(data);
            } catch { /* ignore parse errors */ }
        };
        es.onerror = () => { setConnected(false); setError('SSE connection lost'); es.close(); };
        return () => { es.close(); };
    }, [projectId, enabled]);

    return { connected, lastEvent, error };
}

export default useTaskProgress;
```

### Step 18: Update `frontend/src/pages/ProjectDetailPage.tsx`
Key changes:
1. Import useTaskProgress hook
2. Split fetchAllResults into individual fetch functions (fetchAnalyses, fetchFuzzResults, fetchAuditResults)
3. Add SSE handler that calls the right fetch on each event type
4. Keep startPolling as fallback when SSE is not connected
5. Add project status display and button disable logic

Replace the polling section with:
```typescript
import useTaskProgress from '../hooks/useTaskProgress';

// Split fetchAllResults into individual functions
const fetchAnalyses = useCallback(async () => {
    if (!id) return;
    const res = await client.get(`/v1/projects/${id}/analyses`);
    setAnalyses(res.data);
}, [id]);

const fetchFuzzResults = useCallback(async () => {
    if (!id) return;
    const res = await client.get(`/v1/projects/${id}/fuzz-results`);
    setFuzzResults(res.data);
}, [id]);

const fetchAuditResults = useCallback(async () => {
    if (!id) return;
    const res = await client.get(`/v1/projects/${id}/llm-audit-results`);
    setLlmAuditResults(res.data);
}, [id]);

// SSE connection
const { connected } = useTaskProgress({
    projectId: id || '',
    enabled: triggering !== null,
    onEvent: (event) => {
        if (event.type === 'new_detections') fetchAnalyses();
        if (event.type === 'new_fuzz_results') fetchFuzzResults();
        if (event.type === 'new_audit_results') fetchAuditResults();
        if (event.type === 'status_change') fetchFiles();
        setTriggering(null);
    },
});

// Fallback: use polling when SSE is not connected
useEffect(() => {
    if (triggering && !connected) {
        startPolling();
    }
}, [triggering, connected]);

// Disable buttons when project is not ready
<Button
    type="primary"
    loading={triggering === 'Slither'}
    onClick={() => handleTrigger('Slither', 'analyze')}
    disabled={projectStatus !== 'ready'}
>
    Run Slither
</Button>
```

### Step 19: Update `frontend/src/pages/ReportPage.tsx`
Same pattern:
```typescript
import useTaskProgress from '../hooks/useTaskProgress';

const { connected } = useTaskProgress({
    projectId: id || '',
    enabled: generating,
    onEvent: (event) => {
        if (event.type === 'new_report') {
            fetchReports();
            setGenerating(false);
            message.success('Report generated successfully');
        }
    },
});

// Fallback
useEffect(() => {
    if (generating && !connected) {
        startPolling();
    }
}, [generating, connected]);
```

## Verification Checklist
1. State machine importable: `python -c "from app.state.project_state import ProjectStatus, validate_transition; print('OK')"`
2. Migration runs: `alembic upgrade head` (requires DB)
3. All files parse OK (AST check)
4. models/ from Sprint 1 only has status field added
5. Sprint 2 schemas/ only has status/available_actions added to ProjectResponse
6. Sprint 3 tasks/ only has process_upload modified
7. Sprint 3 engine/ untouched
8. New endpoints registered in router.py
9. Frontend files have no TypeScript syntax errors
