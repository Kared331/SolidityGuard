from typing import Any, List, Optional
from pydantic import BaseModel


class TaskTriggerResponse(BaseModel):
    status: str
    project_id: Optional[int] = None
    task_id: Optional[str] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Any]
