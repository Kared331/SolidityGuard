from datetime import datetime

from pydantic import BaseModel


class ProjectCreateRequest(BaseModel):
    name: str | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str | None
    status: str = "uploaded"
    created_at: datetime | None = None
    available_actions: list[str] = []


class ProjectFileResponse(BaseModel):
    id: int
    file_path: str
    status: str
