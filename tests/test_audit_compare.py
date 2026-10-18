"""两次审计运行对比（新增 / 消失 / 留存）。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.audit_service import compare_audit_runs


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
