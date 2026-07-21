from typing import Optional
from pydantic import BaseModel


class AnalysisTriggerResponse(BaseModel):
    status: str
    project_id: int
    task_id: str


class DetectionResponse(BaseModel):
    id: int
    analysis_result_id: int
    detection_ref: str
    check_name: str
    description: str
    impact: Optional[str] = None
    confidence: Optional[str] = None
