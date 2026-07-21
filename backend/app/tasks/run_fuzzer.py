"""Fuzzing task with meaningful test generation (2.5, 2.6) and error handling (4.14)."""

import logging

from app.celery_app import celery
from app.database import get_sync_session
from app.models import FuzzingResult
from app.services.engine.fuzzer import FuzzerEngine
from app.services.infra.storage import get_project_dir

logger = logging.getLogger("solidiguard.tasks.run_fuzzer")


@celery.task(name="run_fuzzer", bind=True)
def run_fuzzer(self, project_id: int) -> None:
    project_dir = get_project_dir(project_id)
    try:
        self.update_state(state="PROGRESS", meta={"step": "init"})

        engine = FuzzerEngine()
        result = engine.execute(project_id, project_dir)

        with get_sync_session() as session:
            record = FuzzingResult(
                project_id=project_id,
                raw_output=result["raw_output"],
                failures_json=result["failures"],
            )
            session.add(record)
            session.commit()

        self.update_state(state="PROGRESS", meta={"step": "complete"})
        logger.info(
            "Fuzzing completed for project %d: %d failures",
            project_id,
            len(result["failures"]) if result["failures"] else 0,
        )

    except Exception as e:
        logger.exception("Failed to run fuzzer for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(e)})
        raise
