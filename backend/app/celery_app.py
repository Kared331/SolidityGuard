"""Celery application with beat schedule for cleanup (5.20)."""

from celery import Celery
from celery.schedules import crontab

from app.config import REDIS_URL

celery = Celery("solidiguard", broker=REDIS_URL, backend=REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# 5.20: Periodic cleanup of old uploads and reports
celery.conf.beat_schedule = {
    "cleanup-old-files": {
        "task": "app.tasks.cleanup.cleanup_old_files",
        "schedule": crontab(hour=3, minute=0),  # Run daily at 3 AM UTC
    },
}
