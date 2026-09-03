from datetime import datetime

from pydantic import BaseModel


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
    file_paths: dict | None = None
    created_at: datetime
