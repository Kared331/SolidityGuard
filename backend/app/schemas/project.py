from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ProjectCreateRequest(BaseModel):
    name: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: Optional[str]
    status: str = "uploaded"
    created_at: Optional[datetime] = None
    available_actions: List[str] = []


class ProjectFileResponse(BaseModel):
    id: int
    file_path: str
    status: str
