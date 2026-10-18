"""LLM audit task — 文件级并行 + 审计账本。

每个任务 = 一行 audit_runs。两条恒等式必须成立：
    files_total         == files_processed + files_unreadable
    functions_extracted == functions_audited + functions_skipped + functions_failed

并行模型：文件间无依赖，ThreadPoolExecutor(5)；每个线程返回自己的单元列表，
任务层在 as_completed 之后串行合并，因此账本不需要锁。
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import func

from app.celery_app import celery
from app.database import get_sync_session
from app.llm.budget.token_budget import token_budget
from app.llm.config import get_config
from app.llm.pipeline.stream import publish_task_done_sync
from app.models import AuditRun, LLMAuditResult, ProjectFile
from app.services.engine.llm_audit import PROMPT_VERSION, LLMAuditEngine
from app.services.engine.swc_sync import kb_version
from app.services.infra.storage import get_project_file_path

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


def build_coverage(file_results: list[dict], files_total: int) -> dict:
    """Merge per-file results into the run-level ledger (pure, no I/O)."""
    units: list[dict] = []
    warnings: list[dict] = []
    files_processed = 0
    files_unreadable = 0
    rag_failures = 0
    invalid_findings = 0

    for result in file_results:
        units.extend(result.get("units", []))
        warnings.extend(result.get("warnings", []))
        files_processed += result.get("files_processed", 0)
        files_unreadable += result.get("files_unreadable", 0)
        rag_failures += result.get("rag_failures", 0)
        invalid_findings += result.get("invalid_findings", 0)

    audited = sum(1 for u in units if u["status"] == "audited")
    skipped = sum(1 for u in units if u["status"] == "skipped")
    failed = sum(1 for u in units if u["status"] == "failed")
    filtered = sum(1 for u in units if u["status"] == "filtered")
    unchanged = sum(1 for u in units if u["status"] == "unchanged")
    skip_reasons = Counter(u["reason"] for u in units if u["status"] == "skipped" and u.get("reason"))
    fail_reasons = Counter(u["reason"] for u in units if u["status"] == "failed" and u.get("reason"))

    degraded = (skipped + failed + files_unreadable) > 0 or rag_failures > 0

    return {
        "status": "degraded" if degraded else "completed",
        "degraded": degraded,
        "files_total": files_total,
        "files_processed": files_processed,
        "files_unreadable": files_unreadable,
        "functions_extracted": len(units),
        "functions_audited": audited,
        "functions_skipped": skipped,
        "functions_failed": failed,
        "functions_filtered": filtered,
        "functions_unchanged": unchanged,
        "invalid_findings": invalid_findings,
        "rag_hits": sum(1 for u in units if u.get("rag_hits", 0) > 0),
        "rag_failures": rag_failures,
        "skip_reasons": dict(skip_reasons),
        "fail_reasons": dict(fail_reasons),
        "units": units,
        "warnings": warnings,
    }


def _failed_file(reason: str) -> dict:
    """A file whose engine call raised: no units, but counted so F still holds."""
    return {
        "findings": [],
        "units": [],
        "warnings": [{"kind": reason, "file": "", "detail": reason}],
        "functions_audited": 0,
        "files_processed": 0,
        "files_unreadable": 1,
        "rag_failures": 0,
        "invalid_findings": 0,
    }


def _create_run(project_id: int, files_total: int) -> int:
    with get_sync_session() as session:
        run = AuditRun(
            project_id=project_id,
            status="running",
            model=get_config().get_default_provider().defaultModel or None,
            prompt_version=PROMPT_VERSION,
            kb_version=kb_version(),
            files_total=files_total,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def _finish_run(run_id: int, coverage: dict, findings_saved: int, extra: dict | None = None) -> None:
    with get_sync_session() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            return
        run.status = coverage["status"]
        run.files_total = coverage["files_total"]
        run.files_processed = coverage["files_processed"]
        run.files_unreadable = coverage["files_unreadable"]
        run.functions_extracted = coverage["functions_extracted"]
        run.functions_audited = coverage["functions_audited"]
        run.functions_skipped = coverage["functions_skipped"]
        run.functions_failed = coverage["functions_failed"]
        run.functions_filtered = coverage["functions_filtered"]
        run.functions_unchanged = coverage["functions_unchanged"]
        run.invalid_findings = coverage["invalid_findings"]
        run.rag_hits = coverage["rag_hits"]
        run.rag_failures = coverage["rag_failures"]
        details = {"units": coverage["units"], "warnings": coverage["warnings"]}
        if extra:
            details.update(extra)
        run.details_json = details
        run.finished_at = func.now()
        session.commit()

    logger.info(
        "audit run %d: %s %d/%d functions audited, %d saved",
        run_id,
        coverage["status"],
        coverage["functions_audited"],
        coverage["functions_extracted"],
        findings_saved,
    )


def _mark_failed(run_id: int) -> None:
    with get_sync_session() as session:
        run = session.get(AuditRun, run_id)
        if run is not None:
            run.status = "failed"
            run.finished_at = func.now()
            session.commit()


def _save_findings(project_id: int, run_id: int, findings: list[dict]) -> tuple[int, int]:
    saved = 0
    skipped = 0
    if not findings:
        return saved, skipped

    with get_sync_session() as session:
        for finding in findings:
            try:
                session.add(
                    LLMAuditResult(
                        project_id=project_id,
                        audit_run_id=run_id,
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
            logger.info("批量写入 LLM 审计结果: %d saved, %d skipped（单次 commit）", saved, skipped)
        except Exception:
            logger.exception("批量 commit 失败，回滚所有 finding（project_id=%d）", project_id)
            session.rollback()
            skipped = saved
            saved = 0

    return saved, skipped


@celery.task(name="run_llm_audit", bind=True)
def run_llm_audit(self, project_id: int) -> None:
    run_id: int | None = None
    try:
        # P1-7: 从 Redis 载入既有累计 usage，使 check_budget 基线包含重启前消耗
        token_budget.load_usage(project_id)

        with get_sync_session() as session:
            files = session.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()

            file_paths = []
            for pf in files:
                if not pf.file_path.endswith(".sol"):
                    continue
                abs_path = get_project_file_path(project_id, pf.file_path)
                if not os.path.isfile(abs_path):
                    continue
                file_paths.append((pf.id, abs_path))

        files_total = len(file_paths)
        run_id = _create_run(project_id, files_total)

        self.update_state(state="PROGRESS", meta={"step": "start", "files": files_total})

        if not file_paths:
            _finish_run(run_id, build_coverage([], 0), 0)
            publish_task_done_sync(project_id, "new_audit_results", count=0)
            return

        engine = LLMAuditEngine()

        # ── 文件级并行：每个线程处理一个文件 ───────────────────────
        file_results: list[dict] = []
        all_findings: list[dict] = []

        def _collect(result: dict) -> None:
            file_results.append(result)
            all_findings.extend(result.get("findings", []))

        if len(file_paths) == 1:
            file_id, abs_path = file_paths[0]
            try:
                _collect(engine.execute_single_file(project_id, file_id, abs_path))
            except Exception:
                # Same contract as the parallel path: one bad file must not
                # change the run's shape depending on file count.
                logger.exception(
                    "单文件审计失败: project_id=%d, file_id=%d, path=%s",
                    project_id,
                    file_id,
                    abs_path,
                )
                _collect(_failed_file("engine_error"))
        else:
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FILES) as executor:
                future_to_file = {
                    executor.submit(
                        engine.execute_single_file,
                        project_id,
                        file_id,
                        abs_path,
                    ): (file_id, abs_path)
                    for file_id, abs_path in file_paths
                }

                for future in as_completed(future_to_file):
                    file_id, abs_path = future_to_file[future]
                    try:
                        _collect(future.result())
                    except Exception:
                        logger.exception(
                            "文件级并行审计失败: project_id=%d, file_id=%d, path=%s",
                            project_id,
                            file_id,
                            abs_path,
                        )
                        _collect(_failed_file("engine_error"))

        coverage = build_coverage(file_results, files_total)
        saved, skipped = _save_findings(project_id, run_id, all_findings)
        _finish_run(run_id, coverage, saved)

        self.update_state(
            state="PROGRESS",
            meta={
                "step": "complete",
                "functions_audited": coverage["functions_audited"],
                "functions_extracted": coverage["functions_extracted"],
                "findings_saved": saved,
                "findings_skipped": skipped,
                "files_processed": coverage["files_processed"],
                "degraded": coverage["degraded"],
            },
        )
        token_budget.persist_usage(project_id)
        publish_task_done_sync(project_id, "new_audit_results", count=saved)

    except Exception:
        if run_id is not None:
            _mark_failed(run_id)
        logger.exception("LLM audit failed for project %d", project_id)
        raise
