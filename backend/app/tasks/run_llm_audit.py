"""LLM audit task — ThreadPoolExecutor 文件级并行版本。

文件间无数据依赖，使用线程池并行处理。LLM 调用是 I/O 密集型，
线程池足以实现并行加速，且 token_budget 在同进程内加锁共享，
避免跨进程同步开销。

并行度：max_workers=5，与 embedding API 的 Semaphore(5) 对齐，
避免过度并发触发 API rate limit。
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.celery_app import celery
from app.database import get_sync_session
from app.models import LLMAuditResult, ProjectFile
from app.services.engine.llm_audit import LLMAuditEngine
from app.services.infra.storage import get_project_dir, get_project_file_path
from app.llm.budget.token_budget import token_budget

logger = logging.getLogger("solidguard.tasks.run_llm_audit")

# 文件级并行度，与 embedding API Semaphore(5) 对齐
MAX_PARALLEL_FILES = 5

DB_LIMITS = {
    "contract_name": 200,
    "function_name": 200,
    "severity": 50,
}


def _truncate(value: str | None, key: str) -> str | None:
    if value is None:
        return None
    limit = DB_LIMITS.get(key)
    if limit and len(value) > limit:
        return value[:limit]
    return value


@celery.task(name="run_llm_audit", bind=True)
def run_llm_audit(self, project_id: int) -> None:
    try:
        # P1-7: 从 Redis 载入既有累计 usage，使 check_budget 基线包含重启前消耗
        token_budget.load_usage(project_id)

        with get_sync_session() as session:
            files = (
                session.query(ProjectFile)
                .filter(ProjectFile.project_id == project_id)
                .all()
            )

            file_paths = []
            for pf in files:
                if not pf.file_path.endswith(".sol"):
                    continue
                abs_path = get_project_file_path(project_id, pf.file_path)
                if not os.path.isfile(abs_path):
                    continue
                file_paths.append((pf.id, abs_path))

        self.update_state(state="PROGRESS", meta={"step": "start", "files": len(file_paths)})

        if not file_paths:
            self.update_state(
                state="PROGRESS",
                meta={"step": "complete", "functions_audited": 0, "findings_saved": 0, "findings_skipped": 0},
            )
            return

        engine = LLMAuditEngine()

        # ── 文件级并行：ThreadPoolExecutor 并行处理多个文件 ───────
        # 每个线程处理一个文件（summary + 批量 embedding + 逐个 LLM 审计）
        # token_budget 已加 threading.Lock，多线程并发安全
        all_findings: list[dict] = []
        functions_audited = 0
        files_processed = 0

        # 单文件时不创建线程池，减少开销
        if len(file_paths) == 1:
            file_id, abs_path = file_paths[0]
            result = engine.execute_single_file(project_id, file_id, abs_path)
            all_findings.extend(result["findings"])
            functions_audited = result["functions_audited"]
            files_processed = result["files_processed"]
        else:
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FILES) as executor:
                future_to_file = {
                    executor.submit(
                        engine.execute_single_file, project_id, file_id, abs_path,
                    ): (file_id, abs_path)
                    for file_id, abs_path in file_paths
                }

                for future in as_completed(future_to_file):
                    file_id, abs_path = future_to_file[future]
                    try:
                        result = future.result()
                        all_findings.extend(result["findings"])
                        functions_audited += result["functions_audited"]
                        files_processed += result["files_processed"]
                    except Exception:
                        logger.exception(
                            "文件级并行审计失败: project_id=%d, file_id=%d, path=%s",
                            project_id, file_id, abs_path,
                        )

            logger.info(
                "文件级并行审计完成: %d files, %d functions, %d findings（%d 并行线程）",
                len(file_paths), functions_audited, len(all_findings), MAX_PARALLEL_FILES,
            )

        # ── 批量写入：单 session + 单 commit ──────────────────────
        saved = 0
        skipped = 0

        if all_findings:
            with get_sync_session() as session:
                for finding in all_findings:
                    try:
                        session.add(
                            LLMAuditResult(
                                project_id=project_id,
                                contract_name=_truncate(finding["contract_name"], "contract_name"),
                                function_name=_truncate(finding["function_name"], "function_name"),
                                vulnerability_description=finding["vulnerability_description"],
                                severity=_truncate(finding["severity"], "severity"),
                                suggested_fix=finding["suggested_fix"],
                                gas_optimization=finding["gas_optimization"],
                            )
                        )
                        saved += 1
                    except Exception:
                        logger.warning(
                            "Failed to prepare LLM audit finding for %s.%s",
                            _truncate(finding.get("contract_name", "?"), "contract_name"),
                            _truncate(finding.get("function_name", "?"), "function_name"),
                        )
                        skipped += 1

                try:
                    session.commit()
                    logger.info(
                        "批量写入 LLM 审计结果: %d saved, %d skipped（单次 commit）",
                        saved, skipped,
                    )
                except Exception:
                    logger.exception(
                        "批量 commit 失败，回滚所有 finding（project_id=%d）", project_id,
                    )
                    session.rollback()
                    skipped = saved
                    saved = 0

        self.update_state(
            state="PROGRESS",
            meta={
                "step": "complete",
                "functions_audited": functions_audited,
                "findings_saved": saved,
                "findings_skipped": skipped,
                "files_processed": files_processed,
            },
        )
        logger.info(
            "LLM audit completed for project %d: %d saved, %d skipped",
            project_id, saved, skipped,
        )
        # P1-7: 任务结束一次性持久化累计 usage 到 Redis（不做逐调用写库）
        token_budget.persist_usage(project_id)

    except Exception:
        # P0-5: FAILURE 态交由 Celery 原生标记（手动 update_state 破坏结果协议）
        logger.exception("LLM audit failed for project %d", project_id)
        raise
