from pydantic import BaseModel


class FalsePositiveRequest(BaseModel):
    user_note: str | None = None


class FalsePositiveResponse(BaseModel):
    status: str
    detection_ref: str
