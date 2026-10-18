"""Fuzzer 生成器单元测试（不需要 Foundry）。

真实 forge 运行由 `-m integration` 的测试与 worker 探针覆盖；
这里固定的是"生成什么、跳过什么、怎么解析失败"。
"""

import shutil
from pathlib import Path

from app.services.engine.fuzzer import (
    _ctor_value,
    _generate_tests,
    _normalize_param,
    _parse_contracts,
    _parse_failures,
    Param,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _project(tmp_path, filename: str) -> str:
    shutil.copy(FIXTURES / filename, tmp_path / filename)
    return str(tmp_path)


def _parsed(project_dir: str):
    return [
        (c, Path(c.source_path).read_text(encoding="utf-8")) for c in _parse_contracts(project_dir)
    ]


# ─── 参数类型 ────────────────────────────────────────────────────


def test_normalize_supported_types():
    assert _normalize_param("uint256").fuzz_type == "uint256"
    assert _normalize_param("uint8 _x").solidity_type == "uint8"
    assert _normalize_param("address payable to").solidity_type == "address"
    assert _normalize_param("bool ok").fuzz_type == "bool"
    assert _normalize_param("bytes32 h").fuzz_type == "bytes32"


def test_normalize_unsupported_types():
    assert _normalize_param("string memory name").fuzz_type is None
    assert _normalize_param("uint256[] calldata xs").fuzz_type is None


def test_ctor_value_shapes():
    assert _ctor_value(Param("uint8", "uint256")) == "1"
    assert _ctor_value(Param("address", "uint256")) == "address(0x1)"
    assert _ctor_value(Param("string", None)) == '""'
    assert _ctor_value(Param("bytes", None)) == 'hex""'
    assert _ctor_value(Param("uint256[]", None)) is None


# ─── 合约解析 ────────────────────────────────────────────────────


def test_parse_vulnerable_token(tmp_path):
    contracts = _parse_contracts(_project(tmp_path, "VulnerableToken.sol"))

    assert [c.name for c in contracts] == ["VulnerableToken"]
    contract = contracts[0]
    assert len(contract.constructor_params) == 1
    assert contract.constructor_params[0].solidity_type == "uint256"
    names = {f.name for f in contract.functions}
    assert {"transfer", "withdraw", "getBalance"} <= names
    assert contract.rel_import == "../VulnerableToken.sol"


# ─── 生成 ────────────────────────────────────────────────────────


def test_generated_conservation_test_is_real(tmp_path):
    parsed = _parsed(_project(tmp_path, "VulnerableToken.sol"))
    test_dir = tmp_path / "test"

    path, count, reason = _generate_tests(parsed, str(test_dir))

    assert reason == "ok"
    assert count == 1
    text = Path(path).read_text(encoding="utf-8")
    assert 'import "../VulnerableToken.sol";' in text
    assert "new VulnerableToken(uint256(1))" in text
    assert "testFuzz_VulnerableToken_Conservation_withdraw" in text
    assert "assertEq(" in text
    assert "assertEq(x, x)" not in text


def test_no_invariant_yields_no_test(tmp_path):
    parsed = _parsed(_project(tmp_path, "SimpleToken.sol"))

    path, count, reason = _generate_tests(parsed, str(tmp_path / "test"))

    assert path is None
    assert count == 0
    assert reason == "no_invariant_derivable"


# ─── 失败解析 ────────────────────────────────────────────────────


def test_parse_failures_dedupes_and_maps(tmp_path):
    line = (
        "[FAIL: assertion failed: 0 != 1; counterexample: calldata=0xabc args=[1, 2]] "
        "testFuzz_VulnerableToken_Conservation_withdraw(uint256,uint256) (runs: 3, mu: 1)"
    )
    output = f"Suite result\n{line}\nFailing tests:\n{line}\n"

    failures = _parse_failures(output)

    assert len(failures) == 1
    assert failures[0]["contract"] == "VulnerableToken"
    assert failures[0]["function"] == "withdraw"
    assert failures[0]["risk_type"] == "supply_conservation"
    assert failures[0]["counterexample"].startswith("calldata=0xabc")
