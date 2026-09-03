from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FuzzTriggerResponse(BaseModel):
    status: str
    project_id: int
    task_id: str


class FuzzResultResponse(BaseModel):
    id: int
    created_at: datetime
    failures_count: int
    raw_output: str
