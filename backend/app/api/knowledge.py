from fastapi import APIRouter

from app.schemas.knowledge import SyncTriggerResponse
from app.services.knowledge_service import trigger_swc_sync

router = APIRouter()


@router.post("/knowledge/sync", response_model=SyncTriggerResponse)
def trigger_sync(refresh: bool = False):
    """默认读离线快照；`?refresh=true` 才访问上游仓库。"""
    trigger_swc_sync(refresh=refresh)
    return SyncTriggerResponse(status="sync_started")
