"""Incremental LLM audit: only the functions touched by a diff.

The plan (diff -> changed functions) is computed synchronously here and stored
in `audit_runs.details_json["incremental"]`, so the report can show what was
audited, what was skipped as unchanged, and what the diff could not be mapped
to (e.g. a path that is not part of the uploaded project).
"""

from __future__ import annotations

import logging
import os

from app.celery_app import celery
from app.database import get_sync_session
from app.llm.budget.token_budget import token_budget
from app.llm.pipeline.stream import publish_task_done_sync
from app.models import ProjectFile
from app.services.engine.llm_audit import LLMAuditEngine
from app.services.engine.solidity_units import extract_functions
from app.services.incremental import build_plan, parse_unified_diff
from app.services.infra.storage import get_project_file_path
from app.tasks.run_llm_audit import (
    _create_run,
    _failed_file,
    _finish_run,
    _mark_failed,
    _save_findings,
    build_coverage,
)

logger = logging.getLogger("solidguard.tasks.run_incremental_audit")


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _resolve(pf_by_path: dict, path: str, path_map: dict | None):
    normalized = _normalize(path)
    if normalized in pf_by_path:
        return pf_by_path[normalized]
    if path_map:
        mapped = path_map.get(path) or path_map.get(normalized)
        if mapped and _normalize(mapped) in pf_by_path:
            return pf_by_path[_normalize(mapped)]
    basename = os.path.basename(normalized)
    matches = [pf for key, pf in pf_by_path.items() if os.path.basename(key) == basename]
    return matches[0] if len(matches) == 1 else None


@celery.task(name="run_incremental_audit", bind=True)
def run_incremental_audit(self, project_id: int, diff_text: str, path_map: dict | None = None) -> None:
    run_id: int | None = None
    try:
        token_budget.load_usage(project_id)

        with get_sync_session() as session:
            files = session.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            pf_by_path = {_normalize(pf.file_path): pf for pf in files if pf.file_path.endswith(".sol")}

        changed = parse_unified_diff(diff_text)
        if not changed:
            raise ValueError("diff contains no changed .sol hunks")

        resolved = []
        missing = []
        for raw_path, ranges in changed.items():
            pf = _resolve(pf_by_path, raw_path, path_map)
            if pf is None:
                missing.append(raw_path)
                continue
            resolved.append((pf, raw_path, ranges))

        # Every project file enters the ledger: files outside the diff are
        # `unchanged`. Otherwise an incremental run would report coverage over a
        # shrunken denominator (same mistake the keyword filter made).
        changed_ids = {pf.id for pf, _path, _ranges in resolved}
        entries = list(resolved)
        for key, pf in pf_by_path.items():
            if pf.id not in changed_ids:
                entries.append((pf, key, None))

        run_id = _create_run(project_id, len(entries))
        self.update_state(state="PROGRESS", meta={"step": "start", "files": len(entries)})

        engine = LLMAuditEngine()
        results: list[dict] = []
        findings: list[dict] = []
        plan_files: list[dict] = []

        for pf, path, ranges in entries:
            abs_path = get_project_file_path(project_id, pf.file_path)
            if not os.path.isfile(abs_path):
                results.append(_failed_file("read_error"))
                continue

            with open(abs_path, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
            units = extract_functions(text)

            if ranges is None:
                selected: set[tuple[str, int]] = set()
            else:
                plan = build_plan({path: units}, {path: ranges})
                selected = {(u.name, u.line_start) for u in plan.selected}
                file_plan = plan.files[0] if plan.files else None
                plan_files.append(
                    {
                        "file": path,
                        "changed": [u.name for u in plan.selected],
                        "unchanged": [u.name for u in (file_plan.untouched if file_plan else [])],
                        "whole_file": bool(file_plan.whole_file) if file_plan else False,
                        "hunks": len(ranges),
                    }
                )

            result = engine.execute_single_file(project_id, pf.id, abs_path, only_units=selected)
            results.append(result)
            findings.extend(result.get("findings", []))

        coverage = build_coverage(results, len(entries))
        saved, _skipped = _save_findings(project_id, run_id, findings)
        _finish_run(
            run_id,
            coverage,
            saved,
            extra={
                "mode": "incremental",
                "incremental": {
                    "files": plan_files,
                    "missing": missing,
                    "changed_total": coverage["functions_audited"] + coverage["functions_failed"],
                    "unchanged_total": coverage["functions_unchanged"],
                },
            },
        )

        self.update_state(
            state="PROGRESS",
            meta={
                "step": "complete",
                "functions_audited": coverage["functions_audited"],
                "functions_unchanged": coverage["functions_unchanged"],
                "findings_saved": saved,
            },
        )
        token_budget.persist_usage(project_id)
        publish_task_done_sync(project_id, "new_audit_results", count=saved)
        logger.info(
            "incremental audit run %d: %d changed / %d unchanged, %d findings",
            run_id,
            coverage["functions_audited"],
            coverage["functions_unchanged"],
            saved,
        )

    except Exception:
        if run_id is not None:
            _mark_failed(run_id)
        logger.exception("Incremental audit failed for project %d", project_id)
        raise
