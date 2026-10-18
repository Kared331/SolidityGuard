"""P1 账本与可见性：12 + 3 条验收测试。

设计契约见 docs/design/audit-integrity/blueprint.md §P1。
每条测试都对应一个具体断言；实现回退时应当变红。
"""

from unittest.mock import MagicMock

import pytest

from app.models import AuditRun, LLMAuditResult
from app.services.engine.llm_audit import normalize_severity
from app.services.report_generator import aggregate_findings
from app.tasks.cleanup import _delete_project_rows
from app.tasks.run_llm_audit import build_coverage


def _unit(status, reason=None, findings=0, rag_hits=0, name="f"):
    return {
        "file": "Token.sol",
        "function": name,
        "line": 1,
        "status": status,
        "reason": reason,
        "findings": findings,
        "rag_hits": rag_hits,
    }


def _file_result(units, processed=1, unreadable=0, rag_failures=0):
    return {
        "findings": [],
        "units": units,
        "files_processed": processed,
        "files_unreadable": unreadable,
        "rag_failures": rag_failures,
    }


# ─── 1–6 失败矩阵 ────────────────────────────────────────────────


def test_normal_path_completes():
    cov = build_coverage([_file_result([_unit("audited"), _unit("audited", name="g")])], files_total=1)

    assert cov["status"] == "completed"
    assert cov["degraded"] is False
    assert cov["functions_extracted"] == 2
    assert cov["functions_audited"] == 2
    assert cov["functions_skipped"] == 0
    assert cov["functions_failed"] == 0


def test_budget_exhausted_is_skipped_and_degraded():
    cov = build_coverage([_file_result([_unit("skipped", "budget")])], files_total=1)

    assert cov["status"] == "degraded"
    assert cov["functions_skipped"] == 1
    assert cov["skip_reasons"] == {"budget": 1}
    assert cov["functions_audited"] == 0


def test_llm_error_is_failed_and_degraded():
    cov = build_coverage([_file_result([_unit("failed", "llm_error")])], files_total=1)

    assert cov["status"] == "degraded"
    assert cov["functions_failed"] == 1
    assert cov["fail_reasons"] == {"llm_error": 1}


def test_parse_error_is_failed():
    cov = build_coverage([_file_result([_unit("failed", "parse_error")])], files_total=1)

    assert cov["fail_reasons"] == {"parse_error": 1}


def test_rag_failure_degrades_without_losing_coverage():
    cov = build_coverage(
        [_file_result([_unit("audited"), _unit("audited", name="g")], rag_failures=2)],
        files_total=1,
    )

    assert cov["status"] == "degraded"
    assert cov["functions_audited"] == 2
    assert cov["rag_failures"] == 2


def test_unreadable_file_breaks_file_identity_not_function_identity():
    cov = build_coverage([_file_result([], processed=0, unreadable=1)], files_total=1)

    assert cov["status"] == "degraded"
    assert cov["files_unreadable"] == 1
    assert cov["files_processed"] == 0
    assert cov["functions_extracted"] == 0


# ─── 7 恒等式 ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "results,files_total",
    [
        ([_file_result([], processed=1, unreadable=0)], 1),
        ([_file_result([_unit("audited")])], 1),
        ([_file_result([_unit("audited"), _unit("skipped", "budget")])], 1),
        ([_file_result([_unit("failed", "llm_error"), _unit("skipped", "budget"), _unit("audited")])], 1),
        ([_file_result([_unit("audited"), _unit("filtered", "keyword_filter")])], 1),
        ([_file_result([], processed=0, unreadable=1)], 1),
        ([_file_result([_unit("audited")]), _file_result([], processed=0, unreadable=1)], 2),
    ],
)
def test_identities_hold(results, files_total):
    cov = build_coverage(results, files_total)

    assert cov["functions_extracted"] == (
        cov["functions_audited"]
        + cov["functions_skipped"]
        + cov["functions_failed"]
        + cov["functions_filtered"]
    )
    assert cov["files_total"] == cov["files_processed"] + cov["files_unreadable"]


# ─── 8–10 报告 ───────────────────────────────────────────────────


def _llm_row(run_id, name):
    row = MagicMock(spec=LLMAuditResult)
    row.audit_run_id = run_id
    row.contract_name = "Token.sol"
    row.function_name = name
    row.vulnerability_description = "reentrancy"
    row.severity = "High"
    row.suggested_fix = ""
    row.gas_optimization = ""
    return row


def _run(run_id, units, status="completed"):
    run = MagicMock(spec=AuditRun)
    run.id = run_id
    run.status = status
    run.model = "gpt-4o"
    run.prompt_version = "abc12345"
    run.kb_version = "swc-deadbeef"
    run.files_total = 1
    run.files_processed = 1
    run.files_unreadable = 0
    run.functions_extracted = len(units)
    run.functions_audited = sum(1 for u in units if u["status"] == "audited")
    run.functions_skipped = sum(1 for u in units if u["status"] == "skipped")
    run.functions_failed = sum(1 for u in units if u["status"] == "failed")
    run.functions_filtered = sum(1 for u in units if u["status"] == "filtered")
    run.invalid_findings = 0
    run.rag_hits = 0
    run.rag_failures = 0
    run.details_json = {"units": units, "warnings": []}
    return run


def _report_session(latest_run, llm_rows):
    session = MagicMock()

    def _query(model, *args, **kwargs):
        chain = MagicMock()
        chain.join.return_value = chain
        chain.filter.return_value = chain
        chain.order_by.return_value = chain
        if model is AuditRun:
            chain.first.return_value = latest_run
        elif model is LLMAuditResult:
            chain.all.return_value = llm_rows
        else:
            chain.all.return_value = []
        return chain

    session.query.side_effect = _query
    return session


def test_report_uses_only_latest_run():
    units = [_unit("audited")]
    session = _report_session(_run(2, units), [_llm_row(1, "old"), _llm_row(2, "new")])

    result = aggregate_findings(1, session)

    assert [f["function_name"] for f in result["llm_findings"]] == ["new"]
    assert result["audit_coverage"]["run_id"] == 2


def test_report_falls_back_to_legacy_rows_without_run():
    session = _report_session(None, [_llm_row(None, "legacy")])

    result = aggregate_findings(1, session)

    assert [f["function_name"] for f in result["llm_findings"]] == ["legacy"]
    assert result["audit_coverage"]["run_id"] is None


def test_report_coverage_is_consistent_with_run_row():
    units = [_unit("audited"), _unit("skipped", "budget", name="g"), _unit("filtered", "keyword_filter", name="h")]
    session = _report_session(_run(3, units, status="degraded"), [])

    cov = aggregate_findings(1, session)["audit_coverage"]

    assert cov["extracted"] == 3
    assert cov["audited"] == 1
    assert cov["skipped"] == 1
    assert cov["filtered"] == 1
    assert cov["degraded"] is True
    assert cov["skip_reasons"] == {"budget": 1}


def test_html_renders_coverage_section(tmp_path, monkeypatch):
    from app.services import report_generator as rg

    monkeypatch.setattr(rg, "get_report_dir", lambda pid: str(tmp_path))
    coverage = rg.coverage_from_run(
        _run(4, [_unit("audited"), _unit("skipped", "budget", name="g")], status="degraded")
    )
    findings = {
        "slither_findings": [],
        "fuzzing_findings": [],
        "llm_findings": [],
        "audit_coverage": coverage,
    }

    path = rg.generate_html(1, "T", findings)
    html = open(path, encoding="utf-8").read()

    assert "Audit Coverage &amp; Integrity" in html
    assert "50.0%" in html
    assert "Degraded run" in html


def test_polish_preserves_coverage_key():
    from app.services.report_generator import polish_with_llm

    findings = {
        "slither_findings": [],
        "fuzzing_findings": [],
        "llm_findings": [],
        "audit_coverage": {"run_id": 1},
    }

    assert polish_with_llm(findings)["audit_coverage"] == {"run_id": 1}


# ─── 11 清理顺序 ─────────────────────────────────────────────────


def test_cleanup_deletes_findings_before_runs():
    session = MagicMock()
    order = []

    def _query(model, *args, **kwargs):
        chain = MagicMock()
        chain.filter.return_value = chain
        chain.delete.side_effect = lambda *a, **k: order.append(model)
        chain.all.return_value = []
        return chain

    session.query.side_effect = _query
    _delete_project_rows(session, 1)

    assert order.index(LLMAuditResult) < order.index(AuditRun)


# ─── 12 迁移链 ───────────────────────────────────────────────────


def test_migration_014_is_the_single_head():
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = Path(__file__).resolve().parent.parent / "backend"
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    script = ScriptDirectory.from_config(cfg)

    assert script.get_heads() == ["014"]
    assert script.get_revision("014").down_revision == "013"


# ─── 引擎层：状态真的被区分了吗 ─────────────────────────────────


def _fixture_path():
    from pathlib import Path

    return Path(__file__).resolve().parent / "fixtures" / "VulnerableToken.sol"


def _patch_llm(monkeypatch, behaviour):
    from app.services.engine import llm_audit as mod

    monkeypatch.setattr(mod.token_budget, "record_usage", lambda *a, **k: None)
    monkeypatch.setattr(mod, "chat_completion", behaviour)
    return mod


def test_engine_marks_units_audited_and_normalizes_severity(monkeypatch):
    mod = _patch_llm(
        monkeypatch,
        lambda messages: (
            '[{"vulnerability_description": "reentrancy", "severity": "high", '
            '"impact": "drain", "suggested_fix": "checks-effects-interactions", '
            '"confidence": 0.9}]',
            {"total_tokens": 10},
        ),
    )
    monkeypatch.setattr(mod.token_budget, "check_budget", lambda pid: (True, ""))

    result = mod.LLMAuditEngine().execute_single_file(1, 1, str(_fixture_path()))

    assert result["files_processed"] == 1
    assert result["files_unreadable"] == 0
    assert len(result["units"]) == 4
    assert {u["status"] for u in result["units"]} == {"audited"}
    assert result["findings"][0]["severity"] == "High"
    assert sum(u["findings"] for u in result["units"]) == len(result["findings"])


def test_engine_marks_units_skipped_when_budget_is_exhausted(monkeypatch):
    mod = _patch_llm(monkeypatch, lambda messages: ("[]", {"total_tokens": 1}))
    monkeypatch.setattr(mod.token_budget, "check_budget", lambda pid: (False, "exhausted"))

    result = mod.LLMAuditEngine().execute_single_file(1, 1, str(_fixture_path()))

    assert len(result["units"]) == 4
    assert {u["status"] for u in result["units"]} == {"skipped"}
    assert {u["reason"] for u in result["units"]} == {"budget"}
    assert result["findings"] == []


def test_engine_marks_units_failed_on_llm_error(monkeypatch):
    def _boom(messages):
        raise RuntimeError("provider down")

    mod = _patch_llm(monkeypatch, _boom)
    monkeypatch.setattr(mod.token_budget, "check_budget", lambda pid: (True, ""))

    result = mod.LLMAuditEngine().execute_single_file(1, 1, str(_fixture_path()))

    assert {u["status"] for u in result["units"]} == {"failed"}
    assert {u["reason"] for u in result["units"]} == {"llm_error"}
    assert result["findings"] == []


def test_engine_records_keyword_filtered_units(monkeypatch, tmp_path):
    """D1: filtered functions must appear in the ledger, not vanish."""
    mod = _patch_llm(monkeypatch, lambda messages: ("[]", {"total_tokens": 1}))
    monkeypatch.setattr(mod.token_budget, "check_budget", lambda pid: (True, ""))
    contract = tmp_path / "Mix.sol"
    contract.write_text(
        "contract Mix {\n"
        "    uint256 x;\n"
        "    constructor() { x = 1; }\n"
        "    function helper(uint256 a) public pure returns (uint256) { return a + 1; }\n"
        "    function withdraw() public { require(msg.sender == x); }\n"
        "}\n",
        encoding="utf-8",
    )

    result = mod.LLMAuditEngine().execute_single_file(1, 1, str(contract))

    by_name = {u["function"]: u for u in result["units"]}
    assert by_name["helper"]["status"] == "filtered"
    assert by_name["helper"]["reason"] == "keyword_filter"
    assert by_name["withdraw"]["status"] == "audited"
    assert by_name["constructor"]["status"] == "audited"
    assert len(result["units"]) == 3


# ─── severity 归一 ───────────────────────────────────────────────


def test_severity_lowercase_is_normalized():
    assert normalize_severity("high") == "High"


def test_severity_unknown_is_rejected():
    assert normalize_severity("UNKNOWN") is None


def test_severity_missing_is_rejected():
    assert normalize_severity(None) is None
