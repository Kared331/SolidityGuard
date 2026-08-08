import logging

from app.celery_app import celery
from app.database import get_sync_session
from app.models import AnalysisResult, Detection
from app.services.engine.slither import SlitherEngine
from app.services.infra.storage import get_project_dir

logger = logging.getLogger("solidguard.tasks.run_slither")


@celery.task(name="run_slither", bind=True)
def run_slither(self, project_id: int) -> None:
    project_dir = get_project_dir(project_id)
    try:
        self.update_state(state="PROGRESS", meta={"step": "start"})

        engine = SlitherEngine()
        result = engine.execute(project_id, project_dir)

        with get_sync_session() as session:
            record = AnalysisResult(
                project_id=project_id,
                analyzer="slither",
                result_json=result["raw_result"],
            )
            session.add(record)
            session.flush()

            for det in result["detections"]:
                session.add(
                    Detection(
                        analysis_result_id=record.id,
                        detection_ref=det["detection_ref"],
                        check_name=det["check_name"],
                        description=det["description"],
                        impact=det["impact"],
                        confidence=det["confidence"],
                        element_json=det["element_json"],
                    )
                )

            session.commit()

        self.update_state(
            state="PROGRESS",
            meta={"step": "complete", "detection_count": result["detection_count"]},
        )
        logger.info(
            "Slither analysis completed for project %d: %d detections",
            project_id,
            result["detection_count"],
        )

    except Exception as e:
        logger.exception("Failed to save Slither results for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(e)})
        raise
