"""6B: does risk-ranked scheduling find vulnerable contracts faster than order/random?

Setup
-----
Corpus = 143 labeled vulnerable contracts (SmartBugs-curated) + N benign
contracts (the DeFi/library corpus fetched for P5). Labels are directory-based.

Budget B = how many contracts you can audit in one run. A scheduler decides
which B contracts get audited. Because the model only sees what the scheduler
selects, the *scheduling* effect can be measured against labels without calling
the model at all — that keeps the comparison deterministic and free.

Strategies
----------
  alphabetical  sorted path (what a naive upload-order gives)
  random        shuffle, averaged over 200 seeds
  risk          descending count of era-neutral risky constructs
  oracle        all vulnerable contracts first (upper bound, not a baseline)

Metrics at budget B: recall (labeled-vulnerable reached / 143), precision,
distinct vulnerability categories covered.

Usage:
    python docs/evidence/run_6b.py
"""

from __future__ import annotations

import json
import math
import random
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.engine.solidity_units import mask_source  # noqa: E402

CORPUS = ROOT / "corpus"
SMARTBUGS = CORPUS / "smartbugs"
BENIGN_REPOS = ["uniswap-v2-core", "uniswap-v2-periphery", "compound", "openzeppelin", "solmate"]
BUDGETS = [10, 25, 50, 100, 150]

# Era-neutral: these exist in 0.4 and 0.8 alike, so the score does not just
# detect "this file is old".
RISK_PATTERNS = [
    r"\.call\s*[\({]", r"\bdelegatecall\b", r"\bselfdestruct\b", r"\bsuicide\b",
    r"\btx\.origin\b", r"\.send\s*\(", r"\bassembly\b", r"\bmsg\.value\b",
    r"\bblock\.timestamp\b", r"\bblock\.number\b",
]


def risk_score(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    masked = mask_source(text)
    return sum(len(re.findall(pattern, masked)) for pattern in RISK_PATTERNS)


def build_corpus() -> tuple[list[dict], dict[str, str]]:
    labels_meta = json.loads((SMARTBUGS / "labels.json").read_text(encoding="utf-8"))
    labels: dict[str, str] = labels_meta["labels"]

    items = []
    for rel, category in labels.items():
        path = SMARTBUGS / rel
        if path.is_file():
            items.append({"path": path, "rel": rel, "vulnerable": True, "category": category})

    benign_count = 0
    for repo in BENIGN_REPOS:
        for path in sorted((CORPUS / repo).rglob("*.sol")):
            rel = path.relative_to(CORPUS).as_posix()
            if "/test/" in rel or rel.endswith(".t.sol"):
                continue
            items.append({"path": path, "rel": rel, "vulnerable": False, "category": None})
            benign_count += 1

    for item in items:
        item["score"] = risk_score(item["path"])

    return items, labels


def ordering(items: list[dict], strategy: str, rng: random.Random | None = None) -> list[dict]:
    if strategy == "alphabetical":
        return sorted(items, key=lambda x: x["rel"])
    if strategy == "random":
        shuffled = items[:]
        rng.shuffle(shuffled)
        return shuffled
    if strategy == "risk":
        return sorted(items, key=lambda x: (-x["score"], x["rel"]))
    if strategy == "oracle":
        return sorted(items, key=lambda x: (not x["vulnerable"], x["category"] or "~"))
    raise ValueError(strategy)


def metrics(order: list[dict], budget: int) -> dict:
    top = order[:budget]
    vuln = [x for x in top if x["vulnerable"]]
    categories = {x["category"] for x in vuln}
    return {
        "recall": len(vuln) / 143,
        "precision": len(vuln) / budget,
        "categories": len(categories),
    }


def auc(items: list[dict]) -> float:
    """P(score_vulnerable > score_benign), ties counted 0.5."""
    pos = [x["score"] for x in items if x["vulnerable"]]
    neg = [x["score"] for x in items if not x["vulnerable"]]
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    items, _labels = build_corpus()
    vuln_total = sum(1 for x in items if x["vulnerable"])
    benign_total = len(items) - vuln_total
    print(f"corpus: vulnerable={vuln_total} benign={benign_total} total={len(items)}")

    orders = {
        "alphabetical": ordering(items, "alphabetical"),
        "risk": ordering(items, "risk"),
        "oracle": ordering(items, "oracle"),
    }

    table = {}
    for budget in BUDGETS:
        row = {name: metrics(order, budget) for name, order in orders.items()}
        seeds = [metrics(ordering(items, "random", random.Random(s)), budget) for s in range(200)]
        seed_recalls = [m["recall"] for m in seeds]
        row["random"] = {
            "recall": statistics.mean(seed_recalls),
            "precision": statistics.mean(m["precision"] for m in seeds),
            "categories": statistics.mean(m["categories"] for m in seeds),
            "recall_sd": statistics.stdev(seed_recalls),
        }
        # permutation p-value: how often random does at least as well
        at_least = sum(1 for r in seed_recalls if r >= row["risk"]["recall"])
        row["risk"]["p_value"] = (1 + at_least) / (1 + len(seed_recalls))
        table[budget] = row

    score_auc = auc(items)
    cat_scores = {}
    for item in items:
        if item["vulnerable"]:
            cat_scores.setdefault(item["category"], []).append(item["score"])

    report = {
        "corpus": {"vulnerable": vuln_total, "benign": benign_total},
        "score_auc": round(score_auc, 4),
        "by_budget": {
            str(b): {name: {k: round(v, 4) for k, v in m.items()} for name, m in row.items()}
            for b, row in table.items()
        },
        "mean_score_by_category": {k: round(statistics.mean(v), 2) for k, v in sorted(cat_scores.items())},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
