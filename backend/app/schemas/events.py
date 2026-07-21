from typing import Dict, Optional
from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str
    meta: Optional[Dict] = None
