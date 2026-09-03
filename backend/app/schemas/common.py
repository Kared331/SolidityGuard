from typing import Any

from pydantic import BaseModel


class TaskTriggerResponse(BaseModel):
    status: str
    project_id: int | None = None
    task_id: str | None = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]
