from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.detection import FalsePositiveRequest, FalsePositiveResponse
from app.services.detection_service import mark_false_positive

router = APIRouter()


@router.post("/detections/{detection_id}/mark-false-positive", response_model=FalsePositiveResponse)
async def mark_fp(
    detection_id: int,
    body: FalsePositiveRequest = FalsePositiveRequest(),
    db: AsyncSession = Depends(get_db),
):
    fp = await mark_false_positive(db, detection_id, body.user_note)
    return FalsePositiveResponse(status="marked", detection_ref=fp.detection_ref)
