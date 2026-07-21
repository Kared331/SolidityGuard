from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


class FuzzTriggerResponse(BaseModel):
    status: str
    project_id: int
    task_id: str


class FuzzResultResponse(BaseModel):
    id: int
    created_at: datetime
    failures_count: int
    raw_output: str
