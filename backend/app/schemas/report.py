from typing import Dict, Optional
from pydantic import BaseModel
from datetime import datetime


class ReportCreateRequest(BaseModel):
    format: str = "html"


class ReportTriggerResponse(BaseModel):
    status: str
    project_id: int
    format: str
    task_id: str


class ReportListItemResponse(BaseModel):
    id: int
    title: str
    file_paths: Optional[Dict] = None
    created_at: datetime
