from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import async_session
from app.models import Detection, FalsePositiveFeedback

router = APIRouter()


class FalsePositiveRequest(BaseModel):
    user_note: str | None = None


@router.post("/detections/{detection_id}/mark-false-positive")
async def mark_false_positive(detection_id: int, body: FalsePositiveRequest = FalsePositiveRequest()):
    async with async_session() as session:
        detection = await session.get(Detection, detection_id)
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        fp = FalsePositiveFeedback(
            detection_ref=detection.detection_ref,
            user_note=body.user_note,
        )
        session.add(fp)
        await session.commit()

    return {"status": "marked", "detection_ref": detection.detection_ref}
