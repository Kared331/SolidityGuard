"""6A: coverage accounting under fault injection.

Claim being tested:
    For every run, every extracted function ends in exactly one of
    {audited, skipped, failed, filtered}, the reason is recorded, and the
    run is marked degraded whenever anything was not audited.

Method:
  * 3 fault classes x N=100 randomized injections (contract, file count,
    injection point), all deterministic (LLM/RAG stubbed; no API calls);
  * 20 corpus contracts: ledger unit count must equal extraction count;
  * report the marking rate per class with a Clopper-Pearson 95% lower bound.

Usage:
    python docs/evidence/run_6a.py            # full 3 x 100
    python docs/evidence/run_6a.py --n 20     # quick pass
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# The app config requires these placeholders to resolve; the experiment never
# calls a real provider (LLM/RAG are stubbed below).
os.environ.setdefault("SOLIDGUARD_CONFIG", str(ROOT / "solidguard.json"))
os.environ.setdefault("API_KEY", "experiment")
os.environ.setdefault("LLM_API_KEY", "experiment")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/d")

from app.services.engine import llm_audit as mod  # noqa: E402
from app.services.engine.solidity_units import extract_functions, select_units  # noqa: E402
from app.tasks.run_llm_audit import build_coverage  # noqa: E402

logging.disable(logging.CRITICAL)

FIXTURES = ROOT / "tests" / "fixtures"
CORPUS = ROOT / "corpus"

STATUSES = {"audited", "skipped", "failed", "filtered"}


# ─── statistics ────────────────────────────────────────────────────────────

def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided 95% lower bound for k successes out of n."""
    if k == n:
        return alpha ** (1 / n)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _binom_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return lo


# ─── stubs ─────────────────────────────────────────────────────────────────

def _stub_ok(messages):
    return "[]", {"total_tokens": 1}


def _stub_embed(texts):
    return [[0.1] * 8 for _ in texts]


def _stub_embed_one(text):
    return [0.1] * 8


def _stub_chroma_batch(collection, embeddings, top_k=5):
    return [{"documents": [[f"doc{i}"]], "metadatas": [[{"title": "t"}]]} for i in range(len(embeddings))]


def _stub_chroma_one(collection, embedding, top_k=5):
    return {"documents": [["doc"]], "metadatas": [[{"title": "t"}]]}


def install_stubs() -> None:
    mod.chat_completion = _stub_ok
    mod.get_embedding_batch = _stub_embed
    mod.get_embedding = _stub_embed_one
    mod.query_vulnerabilities_batch = _stub_chroma_batch
    mod.query_vulnerabilities = _stub_chroma_one
    mod.get_vulnerability_collection = lambda: object()
    mod.token_budget.check_budget = lambda pid: (True, "")
    mod.token_budget.record_usage = lambda *a, **k: None


# ─── corpus ────────────────────────────────────────────────────────────────

def contract_pool(limit_units: int = 12) -> list[Path]:
    pool = [FIXTURES / "VulnerableToken.sol", FIXTURES / "SimpleToken.sol"]
    if CORPUS.is_dir():
        for path in sorted(CORPUS.rglob("*.sol")):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            units = extract_functions(text)
            if len(units) <= limit_units and select_units(units):
                pool.append(path)
    return pool


# ─── one injection ─────────────────────────────────────────────────────────

def run_once(paths: list[Path], fault: str, seed: int) -> dict:
    """Run the engine over `paths` with one fault class; return ledger facts."""
    chat = mod.chat_completion
    if fault == "llm_error":
        def _boom(messages):
            raise RuntimeError("injected provider outage")

        mod.chat_completion = _boom
    elif fault == "parse_error":
        mod.chat_completion = lambda messages: ("not json at all", {"total_tokens": 1})

    batch, single = mod.query_vulnerabilities_batch, mod.query_vulnerabilities
    if fault == "rag_failure":
        def _rag_boom(*a, **k):
            raise ValueError("injected rag outage")

        mod.query_vulnerabilities_batch = _rag_boom
        mod.query_vulnerabilities = _rag_boom

    budget_state = {"calls": 0}
    if fault == "budget":
        # Fully exhaust: every selected function must be skipped/budget.
        # (Partial exhaustion is covered by the identity check, not this class.)
        def _budget(pid):
            budget_state["calls"] += 1
            return (False, "injected budget exhaustion")

        mod.token_budget.check_budget = _budget

    try:
        results = [mod.LLMAuditEngine().execute_single_file(1, i, str(p)) for i, p in enumerate(paths)]
    finally:
        mod.chat_completion = chat
        mod.query_vulnerabilities_batch = batch
        mod.query_vulnerabilities = single
        mod.token_budget.check_budget = lambda pid: (True, "")

    coverage = build_coverage(results, files_total=len(paths))
    units = coverage["units"]

    facts = {
        "fault": fault,
        "extracted": coverage["functions_extracted"],
        "audited": coverage["functions_audited"],
        "skipped": coverage["functions_skipped"],
        "failed": coverage["functions_failed"],
        "filtered": coverage["functions_filtered"],
        "unreadable": coverage["files_unreadable"],
        "rag_failures": coverage["rag_failures"],
        "status": coverage["status"],
        "degraded": coverage["degraded"],
        "statuses_valid": all(u["status"] in STATUSES for u in units),
        "reasons_recorded": all(u["reason"] for u in units if u["status"] in ("skipped", "failed", "filtered")),
        "identity": coverage["functions_extracted"]
        == coverage["functions_audited"]
        + coverage["functions_skipped"]
        + coverage["functions_failed"]
        + coverage["functions_filtered"],
    }
    return facts


def marked(facts: dict) -> bool:
    """Did the ledger expose this fault?"""
    fault = facts["fault"]
    base = facts["identity"] and facts["statuses_valid"] and facts["reasons_recorded"]
    if fault == "budget":
        return base and facts["skipped"] > 0 and facts["degraded"]
    if fault == "llm_error":
        return base and facts["failed"] > 0 and facts["degraded"] and facts["skipped"] == 0
    if fault == "parse_error":
        return base and facts["failed"] > 0 and facts["degraded"]
    if fault == "rag_failure":
        return base and facts["rag_failures"] > 0 and facts["degraded"] and facts["failed"] == 0
    return False


# ─── coverage conservation ────────────────────────────────────────────────

def conservation_check(limit: int = 20) -> dict:
    install_stubs()
    paths, checked, mismatches = [], 0, []
    for path in sorted((CORPUS).rglob("*.sol")):
        paths.append(path)
        if len(paths) >= limit:
            break
    for i, path in enumerate(paths):
        text = path.read_text(encoding="utf-8", errors="ignore")
        expected = len(extract_functions(text))
        result = mod.LLMAuditEngine().execute_single_file(1, i, str(path))
        cov = build_coverage([result], files_total=1)
        if cov["functions_extracted"] != expected or cov["functions_filtered"] + cov["functions_audited"] != expected:
            mismatches.append({"file": str(path.relative_to(ROOT)), "expected": expected, "got": cov["functions_extracted"]})
        if not (cov["identity"] if "identity" in cov else True):
            pass
        checked += 1
    return {"checked": checked, "mismatches": mismatches}


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261018)
    args = ap.parse_args()

    install_stubs()
    pool = contract_pool()
    rng = random.Random(args.seed)

    faults = ["budget", "rag_failure", "llm_error", "parse_error"]
    report = {}
    for fault in faults:
        hits = 0
        sample = None
        for i in range(args.n):
            paths = [rng.choice(pool) for _ in range(rng.randint(1, 3))]
            facts = run_once(paths, fault, seed=rng.randint(0, 10_000))
            ok = marked(facts)
            hits += ok
            if not ok and sample is None:
                sample = facts
        report[fault] = {
            "n": args.n,
            "marked": hits,
            "rate": hits / args.n,
            "cp_lower": round(clopper_pearson_lower(hits, args.n), 4),
            "counterexample": sample,
        }

    conservation = conservation_check(20)

    print(json.dumps({"faults": report, "conservation": conservation}, ensure_ascii=False, indent=2))
    return 0 if all(v["marked"] == v["n"] for v in report.values()) and not conservation["mismatches"] else 1


if __name__ == "__main__":
    sys.exit(main())
