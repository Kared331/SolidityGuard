"""Map changed line ranges onto function units.

The mapping is deliberately syntactic: a unit is "changed" when its line range
intersects a changed range. That is exact for the common case and, importantly,
explainable — the report can show *why* a function was selected.

Impact surface is reported, not guessed: we list the unchanged functions in the
same file (they share state with the diff) but never claim cross-file/call-graph
impact. Cross-file analysis would require a call graph, which is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.engine.solidity_units import FunctionUnit
from app.services.incremental.diff_parser import LineRange, merge_ranges


@dataclass
class FileChange:
    path: str
    ranges: list[LineRange]
    changed: list[FunctionUnit] = field(default_factory=list)
    untouched: list[FunctionUnit] = field(default_factory=list)
    whole_file: bool = False


@dataclass
class IncrementalPlan:
    files: list[FileChange]
    missing: list[str] = field(default_factory=list)  # changed paths with no parsed units

    @property
    def selected(self) -> list[FunctionUnit]:
        return [unit for change in self.files for unit in change.changed]

    @property
    def selected_count(self) -> int:
        return len(self.selected)

    @property
    def total_count(self) -> int:
        return sum(len(c.changed) + len(c.untouched) for c in self.files)

    @property
    def savings(self) -> float:
        """Fraction of functions that would NOT be audited versus a full run."""
        total = self.total_count
        return round(1 - self.selected_count / total, 4) if total else 0.0


def build_plan(
    units_by_file: dict[str, list[FunctionUnit]],
    changed: dict[str, list[LineRange]],
) -> IncrementalPlan:
    files: list[FileChange] = []
    missing: list[str] = []

    for path, raw_ranges in changed.items():
        units = units_by_file.get(path)
        if units is None:
            missing.append(path)
            continue

        ranges = merge_ranges(raw_ranges)
        change = FileChange(path=path, ranges=ranges)

        if not ranges:
            continue

        for unit in units:
            if any(r.overlaps(unit.line_start, unit.line_end) for r in ranges):
                change.changed.append(unit)
            else:
                change.untouched.append(unit)

        # A diff that touches no function (imports, state vars, comments) still
        # changes the contract's behaviour surface -> audit the whole file.
        if not change.changed and units:
            change.whole_file = True
            change.changed = list(units)
            change.untouched = []

        files.append(change)

    return IncrementalPlan(files=files, missing=missing)
