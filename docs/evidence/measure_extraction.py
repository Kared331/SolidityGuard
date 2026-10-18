"""Measure the Solidity function extractor against a reference scanner.

Usage:
    venv\\Scripts\\python.exe docs\\evidence\\measure_extraction.py
    venv\\Scripts\\python.exe docs\\evidence\\measure_extraction.py --json

Corpus: every unique *.sol under uploads/ (content-hash deduplicated).

Measures the REAL implementation (imports
app.services.engine.solidity_units), so there is no copy to drift.

Two layers are reported separately:
  extract  -> units found (must match the reference: 0 missed / 0 noise)
  select   -> units actually audited (keyword filter still applies: defect D1)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if not os.path.isdir(os.path.join(ROOT, "uploads")):
    ROOT = r"D:\SolidGuard"

sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.services.engine.solidity_units import (  # noqa: E402
    extract_functions,
    mask_source,
    select_units,
)


# ─── reference scanner ─────────────────────────────────────────────────────

_DECL = re.compile(r"\b(function|constructor|receive|fallback)\b")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def reference_extract(source: str) -> list[dict]:
    masked = mask_source(source)
    units = []
    for mt in _DECL.finditer(masked):
        kind = mt.group(1)
        j = mt.end()
        while j < len(masked) and masked[j].isspace():
            j += 1
        if kind == "function":
            ident = _IDENT.match(masked, j)
            if ident is None:
                continue
            name = ident.group(0)
            j = ident.end()
            while j < len(masked) and masked[j].isspace():
                j += 1
        else:
            name = kind
        if j >= len(masked) or masked[j] != "(":
            continue
        depth = 0
        while j < len(masked):
            if masked[j] == "(":
                depth += 1
            elif masked[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        k = j
        while k < len(masked) and masked[k] not in "{;":
            k += 1
        if k >= len(masked) or masked[k] == ";":
            continue
        start = k
        depth = 0
        while k < len(masked):
            if masked[k] == "{":
                depth += 1
            elif masked[k] == "}":
                depth -= 1
                if depth == 0:
                    k += 1
                    break
            k += 1
        units.append({"name": name, "kind": kind, "body": source[start:k]})
    return units


def collect(corpus: str) -> list[tuple[str, str]]:
    seen, files = set(), []
    # `uploads/<id>` layout (app data) or a plain directory (fetched corpus)
    base = os.path.join(corpus, "uploads")
    root = base if os.path.isdir(base) else corpus
    for dirpath, _, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(".sol"):
                continue
            path = os.path.join(dirpath, fn)
            raw = open(path, "rb").read()
            digest = hashlib.sha256(raw).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            files.append((os.path.relpath(path, corpus), raw.decode("utf-8", "replace")))
    return files


SYNTHETIC = {
    "comment_false_positive": "contract C {\n // function fake() { require(msg.sender == owner); }\n function real() public { require(x > 0); }\n}\n",
    "string_brace_truncation": 'contract C {\n function f() public { require(ok, "}"); require(more); }\n}\n',
    "ctor_receive_fallback": "contract C {\n constructor(uint s) { require(s > 0); }\n receive() external payable { bal += msg.value; }\n fallback() external { require(true); }\n function normal() public { require(true); }\n}\n",
    "interface_then_impl": "interface IERC20 {\n function transfer(address to, uint256 amount) external returns (bool);\n}\ncontract Token is IERC20 {\n function transfer(address to, uint256 amount) external returns (bool) {\n  require(bal[msg.sender] >= amount); return true;\n }\n function mint(address to) external { require(to != address(0)); }\n}\n",
    "nested_braces": "contract C {\n function f(uint a) public { for (uint i; i < a; i++) { if (i > 1) { require(i < a); } } }\n}\n",
}


def measure(corpus: str) -> dict:
    files = collect(corpus)
    agg = Counter()
    rows = []

    for path, src in files:
        ref = reference_extract(src)
        units = extract_functions(src)
        selected = select_units(units)

        ref_names = Counter(u["name"] for u in ref)
        unit_names = Counter(u.name for u in units)
        missed = sum(max(0, ref_names[n] - unit_names.get(n, 0)) for n in ref_names)
        noise = sum(max(0, unit_names[n] - ref_names.get(n, 0)) for n in unit_names)

        ref_bodies = defaultdict(list)
        for u in ref:
            ref_bodies[u["name"]].append(len(u["body"]))
        unit_bodies = defaultdict(list)
        for u in units:
            unit_bodies[u.name].append(len(u.body))
        body_mismatch = sum(
            1 for n in ref_bodies
            if sorted(ref_bodies[n]) != sorted(unit_bodies.get(n, []))
        )

        agg["files"] += 1
        agg["bytes"] += len(src)
        agg["ref"] += len(ref)
        agg["units"] += len(units)
        agg["selected"] += len(selected)
        agg["missed"] += missed
        agg["noise"] += noise
        agg["body_mismatch"] += body_mismatch
        agg["ctor"] += sum(1 for u in units if u.kind == "constructor")
        agg["receive"] += sum(1 for u in units if u.kind == "receive")
        agg["fallback"] += sum(1 for u in units if u.kind == "fallback")
        agg["selected_bytes"] += sum(len(u.body) for u in selected)

        rows.append({"path": path, "ref": len(ref), "units": len(units),
                     "selected": len(selected), "missed": missed,
                     "noise": noise, "body_mismatch": body_mismatch})

    synth = {}
    for name, src in SYNTHETIC.items():
        units = extract_functions(src)
        synth[name] = {
            "units": [u.name for u in units],
            "selected": [u.name for u in select_units(units)],
            "reference": [u["name"] for u in reference_extract(src)],
            "body_len": {u.name: len(u.body) for u in units},
        }

    return {
        "corpus": corpus,
        "aggregate": dict(agg),
        "rates": {
            "selected_over_ref": round(agg["selected"] / agg["ref"], 3),
            "missed_over_ref": round(agg["missed"] / agg["ref"], 3),
            "body_bytes_over_file_bytes": round(agg["selected_bytes"] / agg["bytes"], 3),
        },
        "worst_files": sorted(rows, key=lambda r: r["selected"] - r["ref"])[:6],
        "synthetic": synth,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    result = measure(args.corpus)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    a, r = result["aggregate"], result["rates"]
    print(f"corpus: {result['corpus']}")
    print(f"files={a['files']}  bytes={a['bytes']:,}")
    print(f"reference_units={a['ref']}  extracted={a['units']}  "
          f"(missed {a['missed']}, noise {a['noise']}, body_mismatch {a['body_mismatch']})")
    print(f"selected_for_audit={a['selected']}  ({r['selected_over_ref']:.1%} of reference)")
    print(f"special units found: ctor={a['ctor']} receive={a['receive']} fallback={a['fallback']}")
    print(f"audited body bytes = {r['body_bytes_over_file_bytes']:.1%} of file bytes")
    print("\nworst files by selection gap (D1, expected while the filter stays):")
    for row in result["worst_files"]:
        print(f"  selected={row['selected']:>3}/{row['ref']:<3}  units={row['units']:<3}  {row['path']}")
    print("\nsynthetic cases:")
    for name, v in result["synthetic"].items():
        print(f"  {name}: units={v['units']} selected={v['selected']} ref={v['reference']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
