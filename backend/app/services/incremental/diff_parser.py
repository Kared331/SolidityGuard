"""Unified-diff parsing for incremental auditing.

Only what the incremental scheduler needs: which new-file line ranges changed.
Works on `git diff` output; ignores renames/deletions/binary files.

Design note: line numbers are 1-based and inclusive, matching
`FunctionUnit.line_start/line_end`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_NEW_FILE = re.compile(r"^\+\+\+ (?:b/)?(.+)$")


@dataclass(frozen=True)
class LineRange:
    start: int
    end: int

    def overlaps(self, start: int, end: int) -> bool:
        return self.start <= end and start <= self.end


def parse_unified_diff(diff_text: str) -> dict[str, list[LineRange]]:
    """Return {new_path: [changed line ranges]} for a unified diff.

    Added lines produce a range covering them; a pure deletion produces a
    one-line range at the deletion point (so the touched function is still
    selected). Deleted files and binary diffs are skipped.
    """
    changed: dict[str, list[LineRange]] = {}
    path: str | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            match = _NEW_FILE.match(line)
            candidate = match.group(1).strip() if match else ""
            path = None if candidate in ("/dev/null", "") else candidate
            if path is not None:
                changed.setdefault(path, [])
            continue

        if not line.startswith("@@"):
            continue
        hunk = _HUNK.match(line)
        if not hunk or path is None:
            continue

        old_count = int(hunk.group(1)) if hunk.group(1) is not None else 1
        new_start = int(hunk.group(2))
        new_count = int(hunk.group(3)) if hunk.group(3) is not None else 1

        if new_count > 0:
            changed[path].append(LineRange(new_start, new_start + new_count - 1))
        elif old_count > 0:
            # pure deletion: mark the line where content was removed
            anchor = max(1, new_start)
            changed[path].append(LineRange(anchor, anchor))

    return changed


def merge_ranges(ranges: list[LineRange]) -> list[LineRange]:
    """Sort and coalesce overlapping/adjacent ranges."""
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda r: (r.start, r.end))
    merged = [ordered[0]]
    for current in ordered[1:]:
        last = merged[-1]
        if current.start <= last.end + 1:
            merged[-1] = LineRange(last.start, max(last.end, current.end))
        else:
            merged.append(current)
    return merged
