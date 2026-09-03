import os
import tarfile
import zipfile
from pathlib import Path

from app.services.engine.base import BaseEngine


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


class UploadEngine(BaseEngine):
    def execute(self, project_id: int, project_dir: str) -> dict:
        if not os.path.isdir(project_dir):
            self.logger.error("Project directory not found: %s", project_dir)
            return {"sol_files": [], "count": 0}

        # Step 1: Extract any archives found in the project directory
        for fname in os.listdir(project_dir):
            fpath = os.path.join(project_dir, fname)
            if not os.path.isfile(fpath):
                continue

            if fname.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(fpath, "r") as zf:
                        for member in zf.infolist():
                            if not _is_safe_path(project_dir, member.filename):
                                self.logger.warning(
                                    "Zip Slip blocked: %s in archive %s",
                                    member.filename,
                                    fname,
                                )
                                continue
                            zf.extract(member, project_dir)
                except zipfile.BadZipFile:
                    self.logger.warning("Bad zip file: %s", fname)

            elif fname.lower().endswith((".tar.gz", ".tgz")):
                try:
                    with tarfile.open(fpath, "r:gz") as tf:
                        for member in tf.getmembers():
                            # P2-8: 显式拒绝特殊成员（symlink/hardlink/chardev/blockdev/fifo）
                            # 这类成员可能指向 base_dir 外目标或造成其他安全风险，一律不解压；
                            # Python < 3.12 无 extractall(filter="data")，故手动拦截
                            if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
                                self.logger.warning(
                                    "Tar 特殊成员拒绝解压: %s in archive %s",
                                    member.name,
                                    fname,
                                )
                                continue
                            # 复用 _is_safe_path 防护 tar-slip（与 zip 分支一致，A9 约束）
                            if not _is_safe_path(project_dir, member.name):
                                self.logger.warning(
                                    "Tar Slip blocked: %s in archive %s",
                                    member.name,
                                    fname,
                                )
                                continue
                            tf.extract(member, project_dir)
                except tarfile.TarError:
                    self.logger.warning("Bad tar file: %s", fname)

        # Step 2: Delete archive files after extraction
        for fname in os.listdir(project_dir):
            fpath = os.path.join(project_dir, fname)
            if os.path.isfile(fpath) and (fname.lower().endswith((".zip", ".tar.gz", ".tgz"))):
                os.remove(fpath)

        # Step 3: Scan for .sol files
        sol_files = _scan_sol_files(project_dir)
        return {"sol_files": sol_files, "count": len(sol_files)}
