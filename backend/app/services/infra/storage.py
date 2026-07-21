import os

from app.config import settings

UPLOAD_DIR = settings.UPLOAD_DIR
REPORT_DIR = settings.REPORT_DIR


def get_project_dir(project_id: int) -> str:
    return os.path.join(UPLOAD_DIR, str(project_id))


def get_report_dir(project_id: int) -> str:
    return os.path.join(REPORT_DIR, str(project_id))


def get_project_file_path(project_id: int, rel_path: str) -> str:
    return os.path.join(get_project_dir(project_id), rel_path)
