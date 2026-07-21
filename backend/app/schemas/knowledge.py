from typing import List, Optional
from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    status: str


class VulnerabilityItemResponse(BaseModel):
    id: int
    swc_id: str
    title: str
    description: str
    severity: Optional[str] = None
    code_example: Optional[str] = None


class VulnerabilityPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[VulnerabilityItemResponse]
