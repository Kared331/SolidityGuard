"""两次审计运行对比（新增 / 消失 / 留存）。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.audit_service import compare_audit_runs, get_audit_run


def _row(run_id, function, severity="High"):
    row = MagicMock()
    row.audit_run_id = run_id
    row.contract_name = "Token.sol"
    row.function_name = function
    row.severity = severity
    return row


def _run(run_id, status="completed"):
    run = MagicMock()
    run.id = run_id
    run.project_id = 1
    run.status = status
    run.functions_audited = 2
    return run


def _db(rows):
    db = AsyncMock()

    async def _get(model, ident):
        return _run(ident)

    db.get.side_effect = _get
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_compare_classifies_added_removed_persisted():
    rows = [
        _row(1, "withdraw"),
        _row(1, "transfer"),
        _row(2, "withdraw"),
        _row(2, "mint"),
    ]

    out = await compare_audit_runs(_db(rows), 1, 2)

    assert out["counts"] == {"added": 1, "removed": 1, "persisted": 1}
    assert out["added"][0]["function"] == "mint"
    assert out["removed"][0]["function"] == "transfer"
    assert out["persisted"][0]["function"] == "withdraw"
    assert out["base"]["run_id"] == 1 and out["head"]["run_id"] == 2


@pytest.mark.asyncio
async def test_run_detail_exposes_incremental_plan():
    run = MagicMock()
    run.id = 15
    run.status = "completed"
    run.files_total = 2
    run.functions_extracted = 8
    run.functions_audited = 1
    run.functions_skipped = 0
    run.functions_failed = 0
    run.functions_filtered = 0
    run.functions_unchanged = 7
    run.model = "deepseek-chat"
    run.prompt_version = "p"
    run.kb_version = "k"
    run.started_at = run.finished_at = None
    run.details_json = {
        "mode": "incremental",
        "incremental": {"files": [{"file": "A.sol", "changed": ["withdraw"]}], "missing": [], "changed_total": 1, "unchanged_total": 7},
        "units": [{"function": "withdraw", "status": "audited"}],
    }

    db = AsyncMock()
    db.get.return_value = run
    scalar = MagicMock()
    scalar.scalar.return_value = 3
    db.execute.return_value = scalar

    out = await get_audit_run(db, 15)

    assert out["mode"] == "incremental"
    assert out["functions_unchanged"] == 7
    assert out["findings"] == 3
    assert out["incremental"]["changed_total"] == 1
    assert out["units"][0]["function"] == "withdraw"


@pytest.mark.asyncio
async def test_compare_rejects_cross_project():
    db = _db([])

    async def _get(model, ident):
        run = _run(ident)
        run.project_id = 1 if ident == 1 else 2
        return run

    db.get.side_effect = _get

    with pytest.raises(Exception) as exc:
        await compare_audit_runs(db, 1, 2)
    assert "different projects" in str(exc.value)
