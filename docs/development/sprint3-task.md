# Sprint 3: Engine Abstraction + Pipeline Orchestration + Storage Path Unification

## Working Directory
D:\MetaGPT_Project\SolidGuard

## Prerequisites (Sprint 1+2 completed)
- `backend/app/models/` package with 6 files exporting 9 classes
- `backend/app/schemas/` package with 9 files
- `backend/app/dependencies.py` with get_db()
- `backend/app/services/` with 7 business service files + infra files (llm_client.py, embedding.py, chroma_client.py, report_generator.py)
- `backend/app/api/` with 8 thin router handlers
- `backend/app/tasks/` unchanged (still contains original task code)

## Goal
1. Unify all hardcoded file paths into `services/infra/storage.py`
2. Extract core logic from tasks into Engine classes under `services/engine/`
3. Create Pipeline orchestrator under `tasks/pipeline.py`
4. Refactor tasks to lightweight shells (call Engine + DB write + progress update)

## PHASE A: Storage Path Unification

### Step 1: Create `backend/app/services/infra/__init__.py` (empty file)

### Step 2: Create `backend/app/services/infra/storage.py`
```python
import os

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
REPORT_DIR = os.environ.get("REPORT_DIR", "reports")

def get_project_dir(project_id: int) -> str:
    return os.path.join(UPLOAD_DIR, str(project_id))

def get_report_dir(project_id: int) -> str:
    return os.path.join(REPORT_DIR, str(project_id))

def get_project_file_path(project_id: int, rel_path: str) -> str:
    return os.path.join(get_project_dir(project_id), rel_path)
```

### Step 3: Replace ALL hardcoded paths
Files to update:
- `tasks/process_upload.py`: `os.path.join("uploads", str(project_id))` -> `get_project_dir(project_id)`
- `tasks/run_slither.py`: same
- `tasks/run_fuzzer.py`: same
- `tasks/run_llm_audit.py`: `os.path.join("uploads", str(project_id), pf.file_path)` -> `get_project_file_path(project_id, pf.file_path)`
- `tasks/cleanup.py`: `uploads_dir = "uploads"` -> `uploads_dir = UPLOAD_DIR`; `reports_dir = "reports"` -> `reports_dir = REPORT_DIR`
- `services/report_generator.py`: `os.path.join("reports", str(project_id))` -> `get_report_dir(project_id)`
- `services/project_service.py`: `os.path.join("uploads", str(project.id))` -> `get_project_dir(project.id)` (Sprint 2 created this)

## PHASE B: Engine Abstraction Layer

### Step 4: Create `backend/app/services/engine/__init__.py` (empty file)

### Step 5: Create `backend/app/services/engine/base.py`
```python
import logging
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__module__)

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass
```

### Step 6: Create `backend/app/services/engine/upload.py`
Extract from `tasks/process_upload.py`:
- `_is_safe_path(base_dir, target_path)` function (Zip Slip check)
- `_scan_sol_files(directory)` function
- `UploadEngine.execute(project_id, project_dir)` -> returns `{"sol_files": list, "count": int}`
- Includes: zip extraction, tar extraction, archive deletion, sol scanning
- Does NOT include: ProjectFile DB creation (stays in task shell)

### Step 7: Create `backend/app/services/engine/slither.py`
Extract from `tasks/run_slither.py`:
- `_build_detection_ref(detector)` function
- `SlitherEngine.execute(project_id, project_dir)` -> returns `{"raw_result": dict, "detections": list[dict], "detection_count": int}`
- Each detection dict: `{detection_ref, check_name, description, impact, confidence, element_json}`
- Includes: subprocess call, JSON parsing, detection_ref building
- Does NOT include: AnalysisResult/Detection DB write (stays in task shell)

### Step 8: Create `backend/app/services/engine/fuzzer.py`
Extract from `tasks/run_fuzzer.py`:
- `_find_contract_info(project_dir)` function
- `_generate_fuzz_test(contracts, test_dir)` function
- `FuzzerEngine.execute(project_id, project_dir)` -> returns `{"raw_output": str, "failures": list|None, "contracts_found": int, "tests_generated": int}`
- Includes: forge init check, contract scanning, fuzz test generation, forge test run, failure parsing
- Does NOT include: FuzzingResult DB write (stays in task shell)

### Step 9: Create `backend/app/services/engine/llm_audit.py`
Extract from `tasks/run_llm_audit.py`:
- `_extract_key_functions(source_code)` function (with keyword list)
- `LLMAuditEngine.execute(project_id, file_paths)` where file_paths = `[(file_id, abs_path), ...]`
- Returns `{"audit_results": list[dict], "functions_audited": int, "files_processed": int}`
- Each audit_result: `{contract_name, function_name, vulnerability_description, severity, suggested_fix, gas_optimization}`
- Uses existing: chat_completion(), get_embedding(), get_vulnerability_collection()
- Does NOT query DB for files (task passes file_paths)
- Does NOT include: LLMAuditResult DB write (stays in task shell)

### Step 10: Create `backend/app/services/engine/report.py`
Extract from `tasks/generate_report.py`:
- `ReportEngine.execute(project_id, output_format, session)` -> returns `{"file_paths": dict, "title": str, "total_findings": int, "report_content": dict}`
- Uses existing: aggregate_findings(), polish_with_llm(), generate_html(), generate_pdf(), generate_word()
- session parameter needed for aggregate_findings()
- Does NOT include: Report DB write (stays in task shell)

### Step 11: Create `backend/app/services/engine/swc_sync.py`
Extract from `tasks/sync_swc.py`:
- `_fetch_swc_entries()` function (GitHub API)
- `_parse_swc_markdown(raw_content)` function (regex parsing)
- `_generate_and_store_embeddings(entries)` function (Embedding + ChromaDB upsert)
- `SWCSyncEngine.execute()` -> returns `{"entries_synced": int, "parsed_entries": list[dict]}`
- Each parsed_entry: `{swc_id, title, description, severity, code_example}`
- Does NOT include: VulnerabilityEntry DB upsert (stays in task shell)

## PHASE C: Pipeline Orchestrator

### Step 12: Create `backend/app/tasks/pipeline.py`
```python
from celery import chain, group
from app.tasks.run_slither import run_slither
from app.tasks.run_fuzzer import run_fuzzer
from app.tasks.run_llm_audit import run_llm_audit
from app.tasks.generate_report import generate_report
from app.tasks.process_upload import process_upload

def build_analysis_pipeline(project_id: int):
    return chain(run_slither.si(project_id))

def build_fuzz_pipeline(project_id: int):
    return chain(run_fuzzer.si(project_id))

def build_llm_audit_pipeline(project_id: int):
    return chain(run_llm_audit.si(project_id))

def build_report_pipeline(project_id: int, output_format: str):
    return chain(generate_report.si(project_id, output_format))

def build_parallel_analysis_pipeline(project_id: int):
    return group(
        run_slither.si(project_id),
        run_fuzzer.si(project_id),
        run_llm_audit.si(project_id),
    )
```

## PHASE D: Refactor Tasks to Lightweight Shells

### Step 13: Refactor `tasks/process_upload.py`
Structure:
1. `get_project_dir(project_id)` for path
2. `self.update_state(state="PROGRESS", meta={"step": "start"})`
3. Call `UploadEngine().execute(project_id, project_dir)` -> get result
4. DB write: create ProjectFile records, update status to "ready"
5. `self.update_state(state="PROGRESS", meta={"step": "complete", "count": result["count"]})`

### Step 14: Refactor `tasks/run_slither.py`
Structure:
1. `get_project_dir(project_id)` for path
2. `self.update_state(state="PROGRESS", meta={"step": "start"})`
3. Call `SlitherEngine().execute(project_id, project_dir)` -> get result
4. DB write: create AnalysisResult + Detection records
5. `self.update_state(state="PROGRESS", meta={"step": "complete", "detection_count": N})`

### Step 15: Refactor `tasks/run_fuzzer.py`
Structure:
1. `get_project_dir(project_id)` for path
2. `self.update_state(state="PROGRESS", meta={"step": "init"})`
3. Call `FuzzerEngine().execute(project_id, project_dir)` -> get result
4. DB write: create FuzzingResult record
5. `self.update_state(state="PROGRESS", meta={"step": "complete"})`

### Step 16: Refactor `tasks/run_llm_audit.py`
Structure:
1. Query ProjectFile list from DB
2. Build file_paths = [(pf.id, get_project_file_path(project_id, pf.file_path)) for pf in files]
3. `self.update_state(state="PROGRESS", meta={"step": "start"})`
4. Call `LLMAuditEngine().execute(project_id, file_paths)` -> get result
5. DB write: create LLMAuditResult records
6. `self.update_state(state="PROGRESS", meta={"step": "complete", "functions_audited": N})`

### Step 17: Refactor `tasks/generate_report.py`
Structure:
1. `self.update_state(state="PROGRESS", meta={"step": "aggregate"})`
2. Call `ReportEngine().execute(project_id, output_format, session)` -> get result
3. DB write: create Report record
4. `self.update_state(state="PROGRESS", meta={"step": "complete"})`

### Step 18: Refactor `tasks/sync_swc.py`
Structure:
1. `self.update_state(state="PROGRESS", meta={"step": "fetch"})`
2. Call `SWCSyncEngine().execute()` -> get result
3. DB write: upsert VulnerabilityEntry records + ChromaDB embeddings
4. `self.update_state(state="PROGRESS", meta={"step": "complete", "entries_synced": N})`

### Step 19: Update `tasks/cleanup.py`
- Replace `uploads_dir = "uploads"` with `uploads_dir = UPLOAD_DIR`
- Replace `reports_dir = "reports"` with `reports_dir = REPORT_DIR`
- No Engine needed (logic is simple enough)

## PHASE E: Update Service Layer to Use Pipeline

### Step 20: Update `services/analysis_service.py`
- Replace `run_slither.delay(project_id)` with `build_analysis_pipeline(project_id).apply_async()`
- Return `result.id` as task_id

### Step 21: Update `services/fuzz_service.py`
- Replace `run_fuzzer.delay(project_id)` with `build_fuzz_pipeline(project_id).apply_async()`
- Return `result.id` as task_id

### Step 22: Update `services/audit_service.py`
- Replace `run_llm_audit.delay(project_id)` with `build_llm_audit_pipeline(project_id).apply_async()`
- Return `result.id` as task_id

### Step 23: Update `services/report_service.py`
- Replace `generate_report.delay(project_id, fmt)` with `build_report_pipeline(project_id, fmt).apply_async()`
- Return `result.id` as task_id

## Verification
After all changes:
1. grep -rn '"uploads"' backend/app/ -- only in storage.py and config.py
2. grep -rn '"reports"' backend/app/ -- only in storage.py
3. All Engine classes: `python -c "from app.services.engine.upload import UploadEngine; from app.services.engine.slither import SlitherEngine; from app.services.engine.fuzzer import FuzzerEngine; from app.services.engine.llm_audit import LLMAuditEngine; from app.services.engine.report import ReportEngine; from app.services.engine.swc_sync import SWCSyncEngine; print('OK')"`
4. Pipeline: `python -c "from app.tasks.pipeline import build_analysis_pipeline; print('OK')"`
5. All files compile without syntax errors
6. models/ and schemas/ untouched
