import logging

from app.celery_app import celery
from app.database import get_sync_session
from app.models import Project, ProjectFile
from app.services.engine.upload import UploadEngine
from app.services.infra.storage import get_project_dir
from app.state.project_state import ProjectStatus, validate_transition

logger = logging.getLogger("solidguard.tasks.process_upload")


@celery.task(name="process_upload", bind=True)
def process_upload(self, project_id: int) -> None:
    project_dir = get_project_dir(project_id)
    
    # Status: uploaded -> processing
    with get_sync_session() as session:
        project = session.get(Project, project_id)
        if project:
            current = ProjectStatus(project.status)
            if validate_transition(current, ProjectStatus.PROCESSING):
                project.status = ProjectStatus.PROCESSING.value
                session.commit()
    
    try:
        self.update_state(state="PROGRESS", meta={"step": "start"})

        engine = UploadEngine()
        result = engine.execute(project_id, project_dir)

        if result["count"] == 0:
            logger.warning("No .sol files found for project %d", project_id)
            with get_sync_session() as session:
                project = session.get(Project, project_id)
                if project:
                    project.status = ProjectStatus.READY.value
                    session.commit()
            return

        with get_sync_session() as session:
            for rel_path in result["sol_files"]:
                pf = ProjectFile(
                    project_id=project_id,
                    file_path=rel_path,
                    status="ready",
                )
                session.add(pf)

            # Status: processing -> ready (same session)
            project = session.get(Project, project_id)
            if project:
                project.status = ProjectStatus.READY.value

            session.commit()

        self.update_state(
            state="PROGRESS",
            meta={"step": "complete", "count": result["count"]},
        )
        logger.info(
            "Processed upload for project %d: %d .sol files found",
            project_id,
            result["count"],
        )

    except Exception:
        # P0-5: FAILURE 态交由 Celery 原生标记（手动 update_state 破坏结果协议）
        logger.exception("Failed to process upload for project %d", project_id)
        # Keep processing status on failure
        raise
