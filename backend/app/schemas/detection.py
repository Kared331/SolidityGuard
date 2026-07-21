from typing import Optional
from pydantic import BaseModel


class FalsePositiveRequest(BaseModel):
    user_note: Optional[str] = None


class FalsePositiveResponse(BaseModel):
    status: str
    detection_ref: str
