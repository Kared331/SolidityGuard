"""Periodic cleanup task for old uploads and reports (5.20).

Deletes files older than CLEANUP_DAYS (default 30) and removes
corresponding database records.
"""

import logging
import os
import shutil
import time

from app.celery_app import celery
from app.config import CLEANUP_DAYS
from app.database import get_sync_session
from app.models import Project, ProjectFile, Report

logger = logging.getLogger("solidiguard.tasks.cleanup")


def _dir_age_days(path: str) -> float:
    """Return the age of a directory in days since last modification."""
    try:
        mtime = os.path.getmtime(path)
        return (time.time() - mtime) / 86400
    except OSError:
        return 0


@celery.task(name="app.tasks.cleanup.cleanup_old_files", bind=True)
def cleanup_old_files(self):
    """Delete uploads and reports older than CLEANUP_DAYS."""
    cutoff_days = CLEANUP_DAYS
    logger.info("Starting cleanup: deleting files older than %d days", cutoff_days)

    cleaned_projects = 0
    cleaned_reports = 0

    try:
        # ── Clean old uploads ────────────────────────────────────
        uploads_dir = "uploads"
        if os.path.isdir(uploads_dir):
            for entry in os.listdir(uploads_dir):
                project_dir = os.path.join(uploads_dir, entry)
                if not os.path.isdir(project_dir):
                    continue
                age = _dir_age_days(project_dir)
                if age > cutoff_days:
                    try:
                        project_id = int(entry)
                    except ValueError:
                        continue

                    # Remove files from disk
                    shutil.rmtree(project_dir, ignore_errors=True)

                    # Remove database records
                    try:
                        with get_sync_session() as session:
                            session.query(ProjectFile).filter(
                                ProjectFile.project_id == project_id
                            ).delete()
                            session.query(Project).filter(
                                Project.id == project_id
                            ).delete()
                            session.commit()
                    except Exception:
                        logger.exception("Failed to clean DB records for project %d", project_id)

                    cleaned_projects += 1
                    logger.info("Cleaned project %d (age: %.1f days)", project_id, age)

        # ── Clean old reports ────────────────────────────────────
        reports_dir = "reports"
        if os.path.isdir(reports_dir):
            for entry in os.listdir(reports_dir):
                report_dir = os.path.join(reports_dir, entry)
                if not os.path.isdir(report_dir):
                    continue
                age = _dir_age_days(report_dir)
                if age > cutoff_days:
                    shutil.rmtree(report_dir, ignore_errors=True)
                    cleaned_reports += 1
                    logger.info("Cleaned report dir %s (age: %.1f days)", entry, age)

        logger.info(
            "Cleanup complete: %d projects, %d report dirs removed",
            cleaned_projects,
            cleaned_reports,
        )

    except Exception:
        logger.exception("Cleanup task failed")
        self.update_state(state="FAILURE", meta={"exc": str(Exception)})
        raise
