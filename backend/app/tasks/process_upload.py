import logging
import os
import tarfile
import zipfile
from pathlib import Path

from app.celery_app import celery
from app.database import get_sync_session
from app.models import ProjectFile

logger = logging.getLogger("solidiguard.tasks.process_upload")


def _is_safe_path(base_dir: str, target_path: str) -> bool:
    """Check that *target_path* resolves inside *base_dir* (prevents Zip Slip 1.2)."""
    base = Path(base_dir).resolve()
    target = (Path(base_dir) / target_path).resolve()
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def _scan_sol_files(directory: str) -> list[str]:
    """Recursively scan for .sol files, returning paths relative to directory."""
    sol_files: list[str] = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".sol"):
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, directory)
                sol_files.append(rel_path)
    return sol_files


@celery.task(name="process_upload", bind=True)
def process_upload(self, project_id: int) -> None:
    project_dir = os.path.join("uploads", str(project_id))
    if not os.path.isdir(project_dir):
        logger.error("Project directory not found: %s", project_dir)
        return

    try:
        with get_sync_session() as session:
            # Step 1: Extract any archives found in the project directory
            for fname in os.listdir(project_dir):
                fpath = os.path.join(project_dir, fname)
                if not os.path.isfile(fpath):
                    continue

                if fname.lower().endswith(".zip"):
                    try:
                        with zipfile.ZipFile(fpath, "r") as zf:
                            # 1.2: Zip Slip – validate each member path
                            for member in zf.infolist():
                                if not _is_safe_path(project_dir, member.filename):
                                    logger.warning(
                                        "Zip Slip blocked: %s in archive %s",
                                        member.filename,
                                        fname,
                                    )
                                    continue
                            zf.extractall(project_dir)
                    except zipfile.BadZipFile:
                        logger.warning("Bad zip file: %s", fname)

                elif fname.lower().endswith((".tar.gz", ".tgz")):
                    try:
                        with tarfile.open(fpath, "r:gz") as tf:
                            # 1.2: Tar Slip – validate each member path
                            for member in tf.getmembers():
                                member_path = os.path.join(project_dir, member.name)
                                resolved = Path(member_path).resolve()
                                base = Path(project_dir).resolve()
                                try:
                                    resolved.relative_to(base)
                                except ValueError:
                                    logger.warning(
                                        "Tar Slip blocked: %s in archive %s",
                                        member.name,
                                        fname,
                                    )
                                    continue
                            tf.extractall(project_dir)
                    except tarfile.TarError:
                        logger.warning("Bad tar file: %s", fname)

            # Step 2: Delete archive files after extraction
            for fname in os.listdir(project_dir):
                fpath = os.path.join(project_dir, fname)
                if os.path.isfile(fpath) and (
                    fname.lower().endswith((".zip", ".tar.gz", ".tgz"))
                ):
                    os.remove(fpath)

            # Step 3: Scan for .sol files and record them
            sol_files = _scan_sol_files(project_dir)

            file_ids: list[int] = []
            for rel_path in sol_files:
                pf = ProjectFile(
                    project_id=project_id,
                    file_path=rel_path,
                    status="pending",
                )
                session.add(pf)
                session.flush()
                file_ids.append(pf.id)

            session.commit()

            # Step 4: Update status to 'ready'
            for fid in file_ids:
                pf = session.get(ProjectFile, fid)
                if pf:
                    pf.status = "ready"

            session.commit()
            logger.info(
                "Processed upload for project %d: %d .sol files found",
                project_id,
                len(sol_files),
            )

    except Exception:
        logger.exception("Failed to process upload for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(Exception)})
        raise
