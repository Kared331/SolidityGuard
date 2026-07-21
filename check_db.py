import asyncio
from app.database import async_session
from app.models import AnalysisResult, Detection, FuzzingResult, LLMAuditResult
from sqlalchemy import select, func

async def check():
    async with async_session() as s:
        ars = (await s.execute(select(AnalysisResult).where(AnalysisResult.project_id == 41))).scalars().all()
        dets = (await s.execute(select(func.count()).select_from(Detection))).scalar()
        frs = (await s.execute(select(FuzzingResult).where(FuzzingResult.project_id == 41))).scalars().all()
        las = (await s.execute(select(LLMAuditResult).where(LLMAuditResult.project_id == 41))).scalars().all()
        print(f"AnalysisResults={len(ars)}, Detections={dets}, FuzzResults={len(frs)}, LLMAuditResults={len(las)}")
        for fr in frs:
            print(f"  Fuzz: failures={fr.failures_count}, output_len={len(fr.raw_output or '')}")
        for ar in ars:
            print(f"  Analysis: id={ar.id}")

asyncio.run(check())
