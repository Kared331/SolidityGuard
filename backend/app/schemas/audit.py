from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class AuditTriggerResponse(BaseModel):
    status: str
    project_id: int
    task_id: str


class LLMAuditResultResponse(BaseModel):
    id: int
    contract_name: str
    function_name: Optional[str] = None
    vulnerability_description: str
    severity: str
    suggested_fix: Optional[str] = None
    gas_optimization: Optional[str] = None
    created_at: datetime
