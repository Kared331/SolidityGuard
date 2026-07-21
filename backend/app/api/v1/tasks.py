from fastapi import APIRouter

from app.celery_app import celery

router = APIRouter()


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    result = celery.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"task_id": task_id, "state": "PENDING", "meta": None}
    if result.state == "PROGRESS":
        return {"task_id": task_id, "state": "PROGRESS", "meta": result.info}
    if result.state == "SUCCESS":
        return {"task_id": task_id, "state": "SUCCESS", "meta": None}
    if result.state == "FAILURE":
        return {"task_id": task_id, "state": "FAILURE", "meta": {"error": str(result.info)}}
    return {"task_id": task_id, "state": result.state, "meta": None}
