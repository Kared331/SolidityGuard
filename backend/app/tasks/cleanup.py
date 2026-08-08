"""Periodic cleanup task for old uploads and reports (5.20).

Deletes files older than settings.CLEANUP_DAYS (default 30) and removes
corresponding database records.
"""

import logging
import os
import shutil
import time

from app.celery_app import celery
from app.config import settings
from app.database import get_sync_session
from app.models import (
    AnalysisResult,
    Detection,
    FalsePositiveFeedback,
    FuzzingResult,
    LLMAuditResult,
    Project,
    ProjectFile,
    Report,
)
from app.services.infra.storage import REPORT_DIR, UPLOAD_DIR

logger = logging.getLogger("solidguard.tasks.cleanup")


def _dir_age_days(path: str) -> float:
    """Return the age of a directory in days since last modification."""
    try:
        mtime = os.path.getmtime(path)
        return (time.time() - mtime) / 86400
    except OSError:
        return 0


@celery.task(name="app.tasks.cleanup.cleanup_old_files", bind=True)
def cleanup_old_files(self):
    """Delete uploads and reports older than settings.CLEANUP_DAYS."""
    cutoff_days = settings.CLEANUP_DAYS
    logger.info("Starting cleanup: deleting files older than %d days", cutoff_days)

    cleaned_projects = 0
    cleaned_reports = 0

    try:
        # ── Clean old uploads ────────────────────────────────────
        if os.path.isdir(UPLOAD_DIR):
            for entry in os.listdir(UPLOAD_DIR):
                project_dir = os.path.join(UPLOAD_DIR, entry)
                if not os.path.isdir(project_dir):
                    continue
                age = _dir_age_days(project_dir)
                if age > cutoff_days:
                    try:
                        project_id = int(entry)
                    except ValueError:
                        continue

                    shutil.rmtree(project_dir, ignore_errors=True)

                    try:
                        with get_sync_session() as session:
                            # Delete in correct order to respect FK constraints
                            # 1. Delete detections (FK → analysis_results)
                            analysis_ids = [
                                r.id for r in session.query(AnalysisResult.id)
                                .filter(AnalysisResult.project_id == project_id).all()
                            ]
                            if analysis_ids:
                                session.query(Detection).filter(
                                    Detection.analysis_result_id.in_(analysis_ids)
                                ).delete(synchronize_session="fetch")

                            # 2. Delete analysis results, fuzz results, llm audit results, reports, FP
                            session.query(AnalysisResult).filter(
                                AnalysisResult.project_id == project_id
                            ).delete()
                            session.query(FuzzingResult).filter(
                                FuzzingResult.project_id == project_id
                            ).delete()
                            session.query(LLMAuditResult).filter(
                                LLMAuditResult.project_id == project_id
                            ).delete()
                            session.query(Report).filter(
                                Report.project_id == project_id
                            ).delete()
                            session.query(FalsePositiveFeedback).filter(
                                FalsePositiveFeedback.project_id == project_id
                            ).delete()

                            # 3. Delete project files and project
                            session.query(ProjectFile).filter(
                                ProjectFile.project_id == project_id
                            ).delete()
                            session.query(Project).filter(
                                Project.id == project_id
                            ).delete()
                            session.commit()
                    except Exception as e:
                        logger.exception("Failed to clean DB records for project %d: %s", project_id, e)

                    cleaned_projects += 1
                    logger.info("Cleaned project %d (age: %.1f days)", project_id, age)

        # ── Clean old reports ────────────────────────────────────
        if os.path.isdir(REPORT_DIR):
            for entry in os.listdir(REPORT_DIR):
                report_dir = os.path.join(REPORT_DIR, entry)
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

    except Exception as e:
        logger.exception("Cleanup task failed: %s", e)
        self.update_state(state="FAILURE", meta={"exc": str(e)})
        raise
