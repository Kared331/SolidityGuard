from datetime import datetime

from pydantic import BaseModel


class AuditTriggerResponse(BaseModel):
    status: str
    project_id: int
    task_id: str


class IncrementalAuditRequest(BaseModel):
    diff: str
    path_map: dict[str, str] | None = None


class AuditRunSummary(BaseModel):
    id: int
    status: str
    mode: str
    files_total: int
    functions_extracted: int
    functions_audited: int
    functions_skipped: int
    functions_failed: int
    functions_filtered: int
    functions_unchanged: int
    findings: int
    model: str | None = None
    prompt_version: str | None = None
    kb_version: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AuditRunDetail(AuditRunSummary):
    incremental: dict | None = None
    units: list[dict] = []


class LLMAuditResultResponse(BaseModel):
    id: int
    contract_name: str
    function_name: str | None = None
    vulnerability_description: str
    severity: str
    suggested_fix: str | None = None
    gas_optimization: str | None = None
    created_at: datetime
