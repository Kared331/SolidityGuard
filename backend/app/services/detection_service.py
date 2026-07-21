from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisResult, Detection, FalsePositiveFeedback

from fastapi import HTTPException


async def mark_false_positive(db: AsyncSession, detection_id: int, user_note: str | None = None) -> FalsePositiveFeedback:
    detection = await db.get(Detection, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    # Derive project_id from Detection → AnalysisResult → project_id
    analysis_result = await db.get(AnalysisResult, detection.analysis_result_id)
    if not analysis_result:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    fp = FalsePositiveFeedback(
        project_id=analysis_result.project_id,
        detection_ref=detection.detection_ref,
        user_note=user_note,
    )
    db.add(fp)
    await db.commit()
    return fp
