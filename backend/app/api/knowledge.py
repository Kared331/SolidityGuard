from fastapi import APIRouter

from app.tasks.sync_swc import sync_swc

router = APIRouter()


@router.post("/knowledge/sync")
def trigger_sync():
    sync_swc.delay()
    return {"status": "sync_started"}
