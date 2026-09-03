from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    status: str


class VulnerabilityItemResponse(BaseModel):
    id: int
    swc_id: str
    title: str
    description: str
    severity: str | None = None
    code_example: str | None = None


class VulnerabilityPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[VulnerabilityItemResponse]
