"""LLM audit task with improved function extraction (2.10), error handling (4.14),
and per-row DB insertion with field truncation to prevent bulk-failure."""

import logging
import os

from app.celery_app import celery
from app.database import get_sync_session
from app.models import LLMAuditResult, ProjectFile
from app.services.engine.llm_audit import LLMAuditEngine
from app.services.infra.storage import get_project_dir, get_project_file_path

logger = logging.getLogger("solidiguard.tasks.run_llm_audit")

DB_LIMITS = {
    "contract_name": 200,
    "function_name": 200,
    "severity": 50,
}


def _truncate(value: str | None, key: str) -> str | None:
    if value is None:
        return None
    limit = DB_LIMITS.get(key)
    if limit and len(value) > limit:
        return value[:limit]
    return value


@celery.task(name="run_llm_audit", bind=True)
def run_llm_audit(self, project_id: int) -> None:
    try:
        with get_sync_session() as session:
            files = (
                session.query(ProjectFile)
                .filter(ProjectFile.project_id == project_id)
                .all()
            )

            file_paths = []
            for pf in files:
                if not pf.file_path.endswith(".sol"):
                    continue
                abs_path = get_project_file_path(project_id, pf.file_path)
                if not os.path.isfile(abs_path):
                    continue
                file_paths.append((pf.id, abs_path))

        self.update_state(state="PROGRESS", meta={"step": "start"})

        engine = LLMAuditEngine()
        result = engine.execute(project_id, file_paths)

        saved = 0
        skipped = 0
        for finding in result["audit_results"]:
            try:
                with get_sync_session() as session:
                    session.add(
                        LLMAuditResult(
                            project_id=project_id,
                            contract_name=_truncate(finding["contract_name"], "contract_name"),
                            function_name=_truncate(finding["function_name"], "function_name"),
                            vulnerability_description=finding["vulnerability_description"],
                            severity=_truncate(finding["severity"], "severity"),
                            suggested_fix=finding["suggested_fix"],
                            gas_optimization=finding["gas_optimization"],
                        )
                    )
                    session.commit()
                    saved += 1
            except Exception:
                logger.warning(
                    "Failed to save LLM audit finding for %s.%s",
                    _truncate(finding.get("contract_name", "?"), "contract_name"),
                    _truncate(finding.get("function_name", "?"), "function_name"),
                )
                skipped += 1

        self.update_state(
            state="PROGRESS",
            meta={
                "step": "complete",
                "functions_audited": result["functions_audited"],
                "findings_saved": saved,
                "findings_skipped": skipped,
            },
        )
        logger.info(
            "LLM audit completed for project %d: %d saved, %d skipped",
            project_id, saved, skipped,
        )

    except Exception as e:
        logger.exception("LLM audit failed for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(e)})
        raise
