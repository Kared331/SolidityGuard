from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    meta: dict | None = None
