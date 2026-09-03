from datetime import datetime

from pydantic import BaseModel


class AuditTriggerResponse(BaseModel):
    status: str
    project_id: int
    task_id: str


class LLMAuditResultResponse(BaseModel):
    id: int
    contract_name: str
    function_name: str | None = None
    vulnerability_description: str
    severity: str
    suggested_fix: str | None = None
    gas_optimization: str | None = None
    created_at: datetime
