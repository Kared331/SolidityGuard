"""Incremental selection benchmark (synthetic single-function edits).

For every corpus file, we inject a one-line edit inside one function and check
that the incremental plan selects exactly that function. This validates the
diff->function mapping and reports the audit reduction it buys.

Limits (also stated in the evidence doc): diffs are synthetic and one-line;
real git diffs carry context and can span functions/files, which the mapping
handles by design but this harness does not exercise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.engine.solidity_units import extract_functions  # noqa: E402
from app.services.incremental import build_plan, parse_unified_diff  # noqa: E402

CORPUS = ROOT / "corpus"
MAX_FILES = 120
MAX_UNITS_PER_FILE = 2


def make_diff(rel: str, line: int) -> str:
    return (
        f"--- a/{rel}\n"
        f"+++ b/{rel}\n"
        f"@@ -{line},1 +{line},1 @@\n"
        f"-        // original line\n"
        f"+        // mutated line\n"
    )


def main() -> int:
    files = [
        p for p in sorted(CORPUS.rglob("*.sol"))
        if "/smartbugs/" not in p.as_posix() and "/test/" not in p.as_posix() and not p.name.endswith(".t.sol")
    ][:MAX_FILES]

    total = exact = 0
    selected_sum = 0
    unit_sum = 0
    failures = []
    rows = []

    for path in files:
        rel = path.relative_to(CORPUS).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        units = extract_functions(text)
        if len(units) < 3:
            continue

        for unit in units[:MAX_UNITS_PER_FILE]:
            diff = make_diff(rel, unit.line_start)
            plan = build_plan({rel: units}, parse_unified_diff(diff))
            selected = [u.name for u in plan.selected]
            total += 1
            selected_sum += plan.selected_count
            unit_sum += len(units)
            if selected == [unit.name]:
                exact += 1
            else:
                failures.append({"file": rel, "target": unit.name, "selected": selected})

    report = {
        "files": len(files),
        "cases": total,
        "exact_match": exact,
        "exact_rate": round(exact / total, 4) if total else 0.0,
        "avg_selected": round(selected_sum / total, 2) if total else 0,
        "avg_units_per_file": round(unit_sum / total, 2) if total else 0,
        "avg_savings": round(1 - selected_sum / unit_sum, 4) if unit_sum else 0.0,
        "failures": failures[:10],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if exact == total else 1


if __name__ == "__main__":
    sys.exit(main())
