"""Report generation task with unified session (3.9), error handling (4.14),
and LLM data separation (4.17)."""

import logging

from app.celery_app import celery
from app.database import get_sync_session
from app.models import Report
from app.services.engine.report import ReportEngine

logger = logging.getLogger("solidguard.tasks.generate_report")


@celery.task(name="generate_report", bind=True)
def generate_report(self, project_id: int, output_format: str = "html") -> int:
    try:
        self.update_state(state="PROGRESS", meta={"step": "aggregate"})

        with get_sync_session() as session:
            engine = ReportEngine()
            result = engine.execute(project_id, output_format, session)

            report = Report(
                project_id=project_id,
                title=result["title"],
                content_json=result["report_content"],
                file_paths=result["file_paths"],
            )
            session.add(report)
            session.commit()
            session.refresh(report)

        self.update_state(state="PROGRESS", meta={"step": "complete"})
        logger.info(
            "Report generated for project %d (format=%s, id=%d)",
            project_id,
            output_format,
            report.id,
        )
        return report.id

    except Exception:
        # P0-5: FAILURE 态交由 Celery 原生标记——手动 update_state(FAILURE)
        # 会破坏结果后端 FAILURE 协议（KeyError: 'exc_type' 二次异常）
        logger.exception("Report generation failed for project %d", project_id)
        raise
