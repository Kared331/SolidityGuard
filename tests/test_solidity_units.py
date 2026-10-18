"""Tests for the function-unit extractor.

Every test maps to a defect measured on 1.1 MB of real Solidity
(see docs/evidence/extraction-baseline.md):

  D2  interface declarations swallowed the next '{'   -> phantom units
  D3  constructor/receive/fallback never matched
  D4  `function` inside comments treated as real
  D5  '}' inside a string truncated the body
"""

import os

from app.services.engine.solidity_units import extract_functions, select_units


def _names(units):
    return [u.name for u in units]


def test_comment_function_is_ignored():
    """D4: a commented-out function must not become an audit unit."""
    src = """
contract C {
    // function fake() { require(msg.sender == owner); }
    function real() public { require(true); }
}
"""
    assert _names(extract_functions(src)) == ["real"]


def test_string_brace_does_not_truncate_body():
    """D5: '}' inside a string must not end the function body early."""
    src = 'contract C {\n function f() public { require(ok, "}"); require(more); }\n}\n'
    units = extract_functions(src)
    assert len(units) == 1
    assert "require(more)" in units[0].body
    assert units[0].body.rstrip().endswith("}")


def test_interface_declaration_does_not_swallow_next_body():
    """D2: a `;` declaration must not consume the following contract's '{'."""
    src = """
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
}
contract Token is IERC20 {
    function transfer(address to, uint256 amount) external returns (bool) {
        require(amount > 0);
        return true;
    }
    function mint(address to) external { require(to != address(0)); }
}
"""
    units = extract_functions(src)
    assert _names(units) == ["transfer", "mint"]
    assert "require(amount > 0)" in units[0].body
    assert "require(to != address(0))" in units[1].body


def test_constructor_receive_fallback_extracted():
    """D3: the three implicit-entrypoint forms must be units too."""
    src = """
contract C {
    constructor(uint256 s) { require(s > 0); }
    receive() external payable { balance += msg.value; }
    fallback() external { require(true); }
    function normal() public { require(true); }
}
"""
    units = extract_functions(src)
    assert [(u.name, u.kind) for u in units] == [
        ("constructor", "constructor"),
        ("receive", "receive"),
        ("fallback", "fallback"),
        ("normal", "function"),
    ]


def test_selection_keeps_special_functions_but_still_filters_plain_ones():
    """D1 is deferred: plain functions without keywords stay out, special ones never do."""
    src = """
contract C {
    constructor() { x = 1; }
    function helper(uint256 a) public pure returns (uint256) { return a + 1; }
    function withdraw() public { require(msg.sender == owner); }
}
"""
    selected = _names(select_units(extract_functions(src)))
    assert "constructor" in selected
    assert "withdraw" in selected
    assert "helper" not in selected


def test_vulnerable_token_unit_set():
    """D3 on the real fixture: constructor must be present."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", "VulnerableToken.sol")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert _names(extract_functions(src)) == [
        "constructor",
        "transfer",
        "withdraw",
        "getBalance",
    ]


def test_nested_braces_and_line_numbers():
    """Body must survive nesting; line range must cover the whole function."""
    src = """contract C {
    function f(uint256 a) public {
        for (uint256 i; i < a; i++) { if (i > 1) { require(i < a); } }
    }
}
"""
    units = extract_functions(src)
    assert len(units) == 1
    assert units[0].line_start == 2
    assert units[0].line_end == 4
    assert "require(i < a)" in units[0].body
