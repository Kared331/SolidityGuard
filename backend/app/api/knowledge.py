from fastapi import APIRouter

from app.schemas.knowledge import SyncTriggerResponse
from app.services.knowledge_service import trigger_swc_sync

router = APIRouter()


@router.post("/knowledge/sync", response_model=SyncTriggerResponse)
def trigger_sync():
    trigger_swc_sync()
    return SyncTriggerResponse(status="sync_started")
