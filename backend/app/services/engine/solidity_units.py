"""Solidity function-unit extraction.

Deliberately small. Measurements on 1.1 MB of real Solidity
(docs/evidence/extraction-baseline.md) showed the previous regex was 99.2%
accurate on unit boundaries; the defects were specific, not structural:

  D2  a `function f() external;` declaration swallowed the next '{'
  D3  `constructor` / `receive` / `fallback` were never matched at all
  D4  `function` inside a comment was treated as a real function
  D5  '}' inside a string literal truncated the enclosing body

The fix is therefore: mask comments and strings, stop at ';' when looking for
a body, and treat the three implicit-entrypoint forms as first-class units.
No full parser, no AST: that would be defensive engineering for a problem the
corpus does not have (see spec.md §3.1.1 / §6.4 for the escalation trigger).
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

# Kept from the original implementation. Now used ONLY to rank and (for plain
# functions) to select — never to exclude constructors/receive/fallback.
KEYWORDS: tuple[str, ...] = (
    "transfer",
    "call",
    "delegatecall",
    "selfdestruct",
    "send",
    "approve",
    "transferFrom",
    "balance",
    "msg.value",
    "payable",
    "withdraw",
    "deposit",
    "owner",
    "admin",
    "governance",
    "mint",
    "burn",
    "swap",
    "stake",
    "unstake",
    "claim",
    "bridge",
    "kill",
    "pause",
    "unpause",
    "require",
    "assert",
    "add",
    "remove",
    "set",
    "update",
    "execute",
    "vote",
    "propose",
)

FunctionKind = Literal["function", "constructor", "receive", "fallback"]

_DECL = re.compile(r"\b(function|constructor|receive|fallback)\b")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")


@dataclass(frozen=True)
class FunctionUnit:
    name: str
    kind: FunctionKind
    line_start: int
    line_end: int
    body: str
    priority: int


def mask_source(source: str) -> str:
    """Blank comments and string literals, preserving offsets and length."""
    out = list(source)
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            j = source.find("\n", i)
            j = n if j == -1 else j
            out[i:j] = [" "] * (j - i)
            i = j
        elif c == "/" and i + 1 < n and source[i + 1] == "*":
            j = source.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out[i:j] = [" "] * (j - i)
            i = j
        elif c in "\"'":
            quote, j = c, i + 1
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == quote:
                    j += 1
                    break
                j += 1
            out[i:j] = [" "] * (j - i)
            i = j
        else:
            i += 1
    return "".join(out)


def _skip_parens(masked: str, start: int) -> int | None:
    """Return the index just past the matching ')', or None."""
    depth = 0
    i = start
    while i < len(masked):
        ch = masked[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _match_brace(masked: str, start: int) -> int | None:
    """Return the index just past the matching '}', or None."""
    depth = 0
    i = start
    while i < len(masked):
        ch = masked[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _priority(body: str) -> int:
    lowered = body.lower()
    return sum(1 for kw in KEYWORDS if kw in lowered)


def extract_functions(source: str) -> list[FunctionUnit]:
    """Every function-like unit that has a body, in source order."""
    masked = mask_source(source)
    newlines = [i for i, ch in enumerate(source) if ch == "\n"]

    def line_of(offset: int) -> int:
        return bisect_right(newlines, offset - 1) + 1 if offset else 1

    units: list[FunctionUnit] = []
    for match in _DECL.finditer(masked):
        kind = match.group(1)  # type: ignore[assignment]
        j = match.end()
        while j < len(masked) and masked[j].isspace():
            j += 1

        if kind == "function":
            ident = _IDENT.match(masked, j)
            if ident is None:
                # Anonymous fallback (`function () public payable {}`), used by
                # pre-0.6 contracts. A function-type variable declaration
                # (`function (uint) external returns (uint) f;`) also has no
                # name, but ends with ';' -> filtered by the body check below.
                name = "fallback"
                kind = "fallback"
            else:
                name = ident.group(0)
                j = ident.end()
                while j < len(masked) and masked[j].isspace():
                    j += 1
        else:
            name = kind

        if j >= len(masked) or masked[j] != "(":
            continue
        after_params = _skip_parens(masked, j)
        if after_params is None:
            continue

        k = after_params
        while k < len(masked) and masked[k] not in "{;":
            k += 1
        if k >= len(masked) or masked[k] == ";":
            continue  # declaration only (interface / abstract)

        end = _match_brace(masked, k)
        if end is None:
            continue

        body = source[k:end]
        units.append(
            FunctionUnit(
                name=name,
                kind=kind,
                line_start=line_of(match.start()),
                line_end=line_of(end - 1),
                body=body,
                priority=_priority(body),
            )
        )
    return units


def select_units(units: Iterable[FunctionUnit]) -> list[FunctionUnit]:
    """Units to audit, highest priority first.

    Plain functions without any keyword are still skipped: removing that filter
    (defect D1) is a separate decision, because it raises LLM cost.
    constructor / receive / fallback are never filtered — D3 would otherwise
    reappear for exactly the entrypoints that matter most.
    """
    picked = [u for u in units if u.kind != "function" or u.priority > 0]
    return sorted(picked, key=lambda u: (-u.priority, u.line_start))
