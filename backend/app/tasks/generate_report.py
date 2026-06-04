"""Report generation task with unified session (3.9), error handling (4.14),
and LLM data separation (4.17)."""

import logging

from app.celery_app import celery
from app.database import get_sync_session
from app.models import Report
from app.services.report_generator import (
    aggregate_findings,
    generate_html,
    generate_pdf,
    generate_word,
    polish_with_llm,
)

logger = logging.getLogger("solidiguard.tasks.generate_report")


@celery.task(name="generate_report", bind=True)
def generate_report(self, project_id: int, output_format: str = "html") -> int:
    try:
        with get_sync_session() as session:
            raw_findings = aggregate_findings(project_id, session)

            # 4.17: Keep raw findings separate from polished ones
            polished_findings = polish_with_llm(raw_findings)

            title = f'SolidiGuard Audit Report - Project {project_id}'

            file_paths = {}

            if output_format == "html":
                html_path = generate_html(project_id, title, polished_findings)
                file_paths["html"] = html_path
            elif output_format == "pdf":
                html_path = generate_html(project_id, title, polished_findings)
                pdf_path = generate_pdf(html_path)
                file_paths["html"] = html_path
                file_paths["pdf"] = pdf_path
            elif output_format == "word":
                polished_findings["_project_id"] = project_id
                docx_path = generate_word(polished_findings, title)
                file_paths["word"] = docx_path

            # 4.17: Store both raw and polished data in content_json
            report_content = {
                "raw_findings": raw_findings,
                "polished_findings": polished_findings,
            }

            report = Report(
                project_id=project_id,
                title=title,
                content_json=report_content,
                file_paths=file_paths,
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            logger.info("Report generated for project %d (format=%s, id=%d)", project_id, output_format, report.id)
            return report.id

    except Exception:
        logger.exception("Report generation failed for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(Exception)})
        raise
