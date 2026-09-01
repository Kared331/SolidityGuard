"""P0-6: report_generator.aggregate_findings 回归测试（B3 修复固化）。

背景：B3 缺陷——report_generator 假定 element_json 为 dict，而 Slither
真实输出的 elements 是数组，导致报告生成 AttributeError 必崩。B3 已修复
但无测试守护（既有测试将 report_generator 全部 MagicMock，真实逻辑零覆盖）。

红绿验证（V4）：临时回退 B3 修复（删除 isinstance(element, list) 分支）时，
用例 1/3 应变红；恢复后全绿。
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure backend package is importable
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.models import Detection, FalsePositiveFeedback, FuzzingResult, LLMAuditResult
from app.services.report_generator import aggregate_findings


def _make_detection(element_json, detection_ref="slither-001"):
    det = MagicMock()
    det.detection_ref = detection_ref
    det.check_name = "reentrancy-eth"
    det.description = "Reentrancy vulnerability"
    det.impact = "High"
    det.element_json = element_json
    return det


def _make_session(detections, fp_refs=None, fuzz_results=None, llm_results=None):
    """构造 mock session：aggregate_findings 的 4 个 query 链各自返回配置数据。

    注意：真实调用链是 query(...).join(...).filter(...).all()，
    chain 的 join/filter 必须返回自身，否则 .all() 会落到自动生成的
    子 mock 上（迭代为空），导致聚合结果恒为空。
    """
    session = MagicMock()

    def _query(model, *args, **kwargs):
        chain = MagicMock()
        chain.join.return_value = chain
        chain.filter.return_value = chain
        if model is FalsePositiveFeedback.detection_ref:
            chain.all.return_value = list(fp_refs or [])
        elif model is Detection:
            chain.all.return_value = detections
        elif model is FuzzingResult:
            chain.all.return_value = fuzz_results or []
        elif model is LLMAuditResult:
            chain.all.return_value = llm_results or []
        else:
            chain.all.return_value = []
        return chain

    session.query.side_effect = _query
    return session


# ─── B3 回归：element_json 格式兼容 ─────────────────────────────


def test_element_json_list_format():
    """用例 1：element_json 为 list（真实 Slither elements 格式）→ 取首元素 filename_relative。"""
    det = _make_detection([
        {"source_mapping": {"filename_relative": "contracts/Token.sol"}},
        {"source_mapping": {"filename_relative": "contracts/Other.sol"}},
    ])
    session = _make_session([det])

    result = aggregate_findings(1, session)

    assert len(result["slither_findings"]) == 1
    assert result["slither_findings"][0]["code_location"] == "contracts/Token.sol"


def test_element_json_dict_format():
    """用例 2：element_json 为 dict（旧格式兼容）→ 正常取值。"""
    det = _make_detection(
        {"source_mapping": {"filename_relative": "contracts/Token.sol"}}
    )
    session = _make_session([det])

    result = aggregate_findings(1, session)

    assert result["slither_findings"][0]["code_location"] == "contracts/Token.sol"


def test_element_json_none():
    """用例 3：element_json 为 None → code_location 落 N/A 不崩溃。"""
    det = _make_detection(None)
    session = _make_session([det])

    result = aggregate_findings(1, session)

    assert result["slither_findings"][0]["code_location"] == "N/A"


def test_element_json_empty_list():
    """用例 3b：element_json 为空 list → 落 N/A 不崩溃。"""
    det = _make_detection([])
    session = _make_session([det])

    result = aggregate_findings(1, session)

    assert result["slither_findings"][0]["code_location"] == "N/A"


def test_source_mapping_none():
    """用例 4：source_mapping 为 None → 落 N/A 不崩溃。"""
    det = _make_detection([{"source_mapping": None}])
    session = _make_session([det])

    result = aggregate_findings(1, session)

    assert result["slither_findings"][0]["code_location"] == "N/A"


# ─── 误报过滤与多引擎聚合 ────────────────────────────────────────


def test_false_positive_excluded():
    """被标记误报的 detection 不进入报告聚合结果。"""
    det = _make_detection(
        {"source_mapping": {"filename_relative": "a.sol"}}, detection_ref="slither-fp"
    )
    session = _make_session([det], fp_refs=[("slither-fp",)])

    result = aggregate_findings(1, session)

    assert result["slither_findings"] == []


def test_fuzz_failures_list_and_dict_formats():
    """fuzz failures_json 的 list/dict 双格式兼容（B3 同期修复项）。"""
    fr_list = MagicMock()
    fr_list.failures_json = [
        {"test_name": "test_transfer", "counterexample": "balance=0"}
    ]
    fr_dict = MagicMock()
    fr_dict.failures_json = {"test_owner": "revert"}
    session = _make_session([], fuzz_results=[fr_list, fr_dict])

    result = aggregate_findings(1, session)

    titles = {f["title"] for f in result["fuzzing_findings"]}
    assert titles == {"test_transfer", "test_owner"}
