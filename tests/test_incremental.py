"""增量审计地基：diff 解析与函数级映射。"""

from pathlib import Path

from app.services.engine.solidity_units import extract_functions
from app.services.incremental import LineRange, build_plan, merge_ranges, parse_unified_diff

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "VulnerableToken.sol"

DIFF_WITHDRAW = """diff --git a/contracts/VulnerableToken.sol b/contracts/VulnerableToken.sol
index 1111111..2222222 100644
--- a/contracts/VulnerableToken.sol
+++ b/contracts/VulnerableToken.sol
@@ -22,7 +22,7 @@ contract VulnerableToken {
     // Vulnerable: unchecked external call
     function withdraw(uint256 _amount) public {
         require(balances[msg.sender] >= _amount, "Insufficient balance");
-        (bool success, ) = msg.sender.call{value: _amount}("");
+        (bool success, ) = msg.sender.call{value: _amount}(""); // touched
         require(success, "Transfer failed");
         balances[msg.sender] -= _amount;
     }
"""


def _units():
    return {"contracts/VulnerableToken.sol": extract_functions(FIXTURE.read_text(encoding="utf-8"))}


# ─── diff 解析 ───────────────────────────────────────────────────


def test_parse_single_hunk():
    changed = parse_unified_diff(DIFF_WITHDRAW)

    assert changed == {"contracts/VulnerableToken.sol": [LineRange(22, 28)]}


def test_parse_multiple_files_and_hunks():
    diff = """diff --git a/A.sol b/A.sol
--- a/A.sol
+++ b/A.sol
@@ -1,2 +1,3 @@
+// new line
 a
 b
@@ -10,3 +11,3 @@
 x
-y
+z
 w
diff --git a/B.sol b/B.sol
--- a/B.sol
+++ b/B.sol
@@ -5,0 +6,2 @@
+one
+two
"""

    changed = parse_unified_diff(diff)

    assert changed["A.sol"] == [LineRange(1, 3), LineRange(11, 13)]
    assert changed["B.sol"] == [LineRange(6, 7)]


def test_pure_deletion_marks_anchor_line():
    diff = """--- a/X.sol
+++ b/X.sol
@@ -10,2 +9,0 @@
-gone1
-gone2
"""

    assert parse_unified_diff(diff) == {"X.sol": [LineRange(9, 9)]}


def test_deleted_file_is_skipped():
    diff = """--- a/X.sol
+++ /dev/null
@@ -1,3 +0,0 @@
-a
-b
-c
"""

    assert parse_unified_diff(diff) == {}


def test_merge_ranges_coalesces():
    merged = merge_ranges([LineRange(10, 12), LineRange(1, 2), LineRange(13, 14), LineRange(2, 3)])

    assert merged == [LineRange(1, 3), LineRange(10, 14)]


# ─── 映射 ────────────────────────────────────────────────────────


def test_plan_selects_only_changed_function():
    plan = build_plan(_units(), parse_unified_diff(DIFF_WITHDRAW))

    assert [u.name for u in plan.selected] == ["withdraw"]
    assert plan.selected_count == 1
    assert plan.total_count == 4
    assert plan.savings == 0.75
    assert plan.files[0].whole_file is False


def test_plan_reports_context_functions_as_untouched():
    plan = build_plan(_units(), parse_unified_diff(DIFF_WITHDRAW))

    untouched = {u.name for u in plan.files[0].untouched}
    assert untouched == {"constructor", "transfer", "getBalance"}


def test_non_function_change_falls_back_to_whole_file():
    # line 6 is the `mapping(address => uint256) public balances;` declaration
    diff = """--- a/contracts/VulnerableToken.sol
+++ b/contracts/VulnerableToken.sol
@@ -6,3 +6,3 @@
-    mapping(address => uint256) public balances;
+    mapping(address => uint256) public balances;
     uint256 public totalSupply;
"""

    plan = build_plan(_units(), parse_unified_diff(diff))

    assert plan.files[0].whole_file is True
    assert plan.selected_count == 4
    assert plan.savings == 0.0


def test_unknown_path_is_reported_not_crashed():
    diff = """--- a/contracts/Unknown.sol
+++ b/contracts/Unknown.sol
@@ -1,1 +1,1 @@
-a
+b
"""

    plan = build_plan(_units(), parse_unified_diff(diff))

    assert plan.missing == ["contracts/Unknown.sol"]
    assert plan.selected_count == 0
