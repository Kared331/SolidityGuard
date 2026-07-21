# Sprint 2: Service Layer Abstraction + Schema Definition

## Working Directory
D:\MetaGPT_Project\SolidGuard

## Prerequisites (Sprint 1 completed)
- `backend/app/models/` package exists with 6 files exporting 9 classes
- `backend/app/models_old.py` backup exists
- Original `backend/app/models.py` has been deleted

## Goal
API handler becomes thin router. Business logic moves to Service layer. Pydantic schemas define request/response.

## PHASE A: Create Schemas

### Step 1: Create `backend/app/schemas/__init__.py` (empty)

### Step 2: Create `backend/app/schemas/common.py`
```python
from __future__ import annotations
from pydantic import BaseModel
from typing import Any

class TaskTriggerResponse(BaseModel):
    status: str
    project_id: int | None = None
    task_id: str | None = None

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]
```

### Step 3: Create `backend/app/schemas/project.py`
```python
from __future__ import annotations
from pydantic import BaseModel

class ProjectCreateRequest(BaseModel):
    name: str | None = None

class ProjectResponse(BaseModel):
    id: int
    name: str | None

class ProjectFileResponse(BaseModel):
    id: int
    file_path: str
    status: str
```

### Step 4: Create `backend/app/schemas/analysis.py`
```python
from __future__ import annotations
from pydantic import BaseModel

class AnalysisTriggerResponse(BaseModel):
    status: str
    project_id: int

class DetectionResponse(BaseModel):
    id: int
    analysis_result_id: int
    detection_ref: str
    check_name: str
    description: str
    impact: str | None = None
    confidence: str | None = None
```

### Step 5: Create `backend/app/schemas/fuzz.py`
```python
from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime

class FuzzTriggerResponse(BaseModel):
    status: str
    project_id: int

class FuzzResultResponse(BaseModel):
    id: int
    created_at: datetime
    failures_count: int
    raw_output: str
```

### Step 6: Create `backend/app/schemas/audit.py`
```python
from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime

class AuditTriggerResponse(BaseModel):
    status: str
    project_id: int

class LLMAuditResultResponse(BaseModel):
    id: int
    contract_name: str
    function_name: str | None = None
    vulnerability_description: str
    severity: str
    suggested_fix: str | None = None
    gas_optimization: str | None = None
    created_at: datetime
```

### Step 7: Create `backend/app/schemas/detection.py`
```python
from __future__ import annotations
from pydantic import BaseModel

class FalsePositiveRequest(BaseModel):
    user_note: str | None = None

class FalsePositiveResponse(BaseModel):
    status: str
    detection_ref: str
```

### Step 8: Create `backend/app/schemas/report.py`
```python
from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime

class ReportCreateRequest(BaseModel):
    format: str = "html"

class ReportTriggerResponse(BaseModel):
    status: str
    project_id: int
    format: str

class ReportListItemResponse(BaseModel):
    id: int
    title: str
    file_paths: dict | None = None
    created_at: datetime
```

### Step 9: Create `backend/app/schemas/knowledge.py`
```python
from __future__ import annotations
from pydantic import BaseModel

class SyncTriggerResponse(BaseModel):
    status: str

class VulnerabilityItemResponse(BaseModel):
    id: int
    swc_id: str
    title: str
    description: str
    severity: str | None = None
    code_example: str | None = None

class VulnerabilityPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[VulnerabilityItemResponse]
```

## PHASE B: Create dependencies.py

### Step 10: Create `backend/app/dependencies.py`
```python
from app.database import async_session
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db():
    async with async_session() as session:
        yield session
```

## PHASE C: Create Business Services

### Step 11: Create `backend/app/services/project_service.py`
Extract from `api/projects.py`:
- File validation constants (ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES, magic bytes)
- `_verify_magic_bytes()`, `_validate_filename()` functions
- `create_project_with_files(db, name, files)` -> creates Project, writes files, dispatches process_upload.delay()
- `get_project_files(db, project_id)` -> returns list of ProjectFile
- `get_project_or_404(db, project_id)` -> returns Project or raises 404

### Step 12: Create `backend/app/services/analysis_service.py`
Extract from `api/analysis.py`:
- `trigger_analysis(db, project_id)` -> checks project exists, dispatches run_slither.delay()
- `list_analyses_filtered(db, project_id)` -> queries detections, filters false positives

### Step 13: Create `backend/app/services/fuzz_service.py`
Extract from `api/fuzz.py`:
- `trigger_fuzz(db, project_id)` -> checks project, dispatches run_fuzzer.delay()
- `list_fuzz_results(db, project_id)` -> queries FuzzingResult, truncates raw_output

### Step 14: Create `backend/app/services/audit_service.py`
Extract from `api/llm_audit.py`:
- `trigger_llm_audit(db, project_id)` -> checks project, dispatches run_llm_audit.delay()
- `list_llm_audit_results(db, project_id)` -> queries LLMAuditResult

### Step 15: Create `backend/app/services/detection_service.py`
Extract from `api/detections.py`:
- `mark_false_positive(db, detection_id, user_note)` -> checks detection, creates FalsePositiveFeedback

### Step 16: Create `backend/app/services/report_service.py`
Extract from `api/reports.py`:
- `trigger_report(db, project_id, format)` -> validates format, dispatches generate_report.delay()
- `list_reports(db, project_id)` -> queries Report
- `get_report_download_info(db, report_id, format)` -> returns (file_path, media_type, filename) or raises 404

### Step 17: Create `backend/app/services/knowledge_service.py`
Extract from `api/knowledge.py` + `api/vulnerabilities.py`:
- `trigger_swc_sync()` -> dispatches sync_swc.delay()
- `search_vulnerabilities(db, search, page, page_size)` -> queries VulnerabilityEntry with pagination

## PHASE D: Refactor API handlers

### Step 18: Refactor `backend/app/api/projects.py`
- Remove all SQLAlchemy queries
- Remove file validation logic (moved to service)
- Import from project_service, schemas
- Handler only: extract params -> call service -> return schema
- Keep file upload handling (UploadFile) in handler

### Step 19-25: Refactor remaining API files
Same pattern for analysis.py, fuzz.py, llm_audit.py, detections.py, reports.py, knowledge.py, vulnerabilities.py

## Verification Checklist
After all changes, verify:
1. All files have correct imports (no circular dependencies)
2. API response format unchanged
3. No SQLAlchemy in API handlers
4. Services receive db: AsyncSession
5. Celery dispatch stays in services
