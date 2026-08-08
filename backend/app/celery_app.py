"""Celery application with beat schedule for cleanup (5.20)."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery("solidguard", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_shutdown_timeout=30,
)

# 5.20: Periodic cleanup of old uploads and reports
celery.autodiscover_tasks(["app.tasks"])

celery.conf.beat_schedule = {
    "cleanup-old-files": {
        "task": "app.tasks.cleanup.cleanup_old_files",
        "schedule": crontab(hour=3, minute=0),  # Run daily at 3 AM UTC
    },
}
