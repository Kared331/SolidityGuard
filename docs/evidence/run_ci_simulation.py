"""CI simulation for the incremental audit endpoint.

Runs the same commands as `.github/workflows/solidguard-incremental.yml.example`
on a real git repository, against a running SolidiGuard stack:

    git init -> base commit -> edit withdraw -> head commit
    git diff --no-color HEAD~1...HEAD -- '*.sol'  > patch
    zip working tree -> POST /projects
    POST /llm-audit            (baseline full run)
    POST /incremental-audit    (patch)
    GET  /runs/{a}/compare/{b}

Difference from GitHub: only *who* runs these commands. The diff format, the
endpoint, the payload and the runner's reachability requirements are identical.

Requires: docker compose up -d, LLM_API_KEY configured.
Usage: python docs/evidence/run_ci_simulation.py
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / ".tmp" / "ci-sim"
BASE = "http://127.0.0.1:8000"
FIXTURES = ROOT / "tests" / "fixtures"

TOKEN = (FIXTURES / "VulnerableToken.sol").read_text(encoding="utf-8")
SIMPLE = (FIXTURES / "SimpleToken.sol").read_text(encoding="utf-8")


def api_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("API_KEY missing in .env")


def run(cmd: list[str], cwd: Path) -> str:
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise SystemExit(f"{cmd} failed: {out.stderr[:400]}")
    return out.stdout


def build_repo() -> Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "contracts").mkdir(parents=True)

    (WORK / "contracts" / "Token.sol").write_text(TOKEN, encoding="utf-8")
    (WORK / "contracts" / "Simple.sol").write_text(SIMPLE, encoding="utf-8")

    run(["git", "init", "-q"], WORK)
    run(["git", "config", "user.email", "ci@example.com"], WORK)
    run(["git", "config", "user.name", "ci"], WORK)
    run(["git", "add", "-A"], WORK)
    run(["git", "commit", "-qm", "base"], WORK)

    # Semantic edit: insert a guard line inside withdraw (shifts line numbers).
    token_path = WORK / "contracts" / "Token.sol"
    text = token_path.read_text(encoding="utf-8")
    text = text.replace(
        '        require(balances[msg.sender] >= _amount, "Insufficient balance");',
        '        require(balances[msg.sender] >= _amount, "Insufficient balance");\n'
        '        require(_amount > 0, "zero amount");',
    )
    token_path.write_text(text, encoding="utf-8")
    run(["git", "add", "-A"], WORK)
    run(["git", "commit", "-qm", "head"], WORK)
    return WORK


def make_patch(repo: Path) -> str:
    return run(["git", "diff", "--no-color", "HEAD~1...HEAD", "--", "*.sol"], repo)


def make_zip(repo: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in sorted(repo.rglob("*")):
            if path.is_file() and ".git" not in path.parts:
                zf.write(path, path.relative_to(repo).as_posix())
    return buf.getvalue()


def wait(fn, timeout: float, label: str):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(2)
    raise SystemExit(f"timeout waiting for {label}")


def main() -> int:
    repo = build_repo()
    patch = make_patch(repo)
    print(f"patch bytes={len(patch)} files={patch.count('+++ b/')}")

    client = httpx.Client(base_url=BASE, headers={"X-API-Key": api_key()}, timeout=120)
    resp = client.post(
        "/api/v1/projects",
        files={"files": ("repo.zip", make_zip(repo), "application/zip")},
        data={"name": f"ci-sim-{int(time.time())}"},
    )
    resp.raise_for_status()
    pid = resp.json()["id"]
    print("project", pid)

    wait(lambda: client.get(f"/api/v1/projects/{pid}/files").json() or None, 60, "files")

    # baseline full run
    client.post(f"/api/v1/projects/{pid}/llm-audit").raise_for_status()
    runs = wait(lambda: client.get(f"/api/v1/projects/{pid}/runs").json() or None, 60, "run A")
    run_a = runs[0]["id"]
    wait(
        lambda: next(
            (r for r in client.get(f"/api/v1/projects/{pid}/runs").json() if r["id"] == run_a and r["status"] != "running"),
            None,
        ),
        600,
        "run A done",
    )

    # incremental run from the CI patch
    resp = client.post(f"/api/v1/projects/{pid}/incremental-audit", json={"diff": patch})
    resp.raise_for_status()
    run_b = wait(
        lambda: next(
            (
                r["id"]
                for r in client.get(f"/api/v1/projects/{pid}/runs").json()
                if r["id"] > run_a and r["mode"] == "incremental"
            ),
            None,
        ),
        120,
        "run B",
    )
    wait(
        lambda: next(
            (r for r in client.get(f"/api/v1/projects/{pid}/runs").json() if r["id"] == run_b and r["status"] != "running"),
            None,
        ),
        600,
        "run B done",
    )

    detail = client.get(f"/api/v1/runs/{run_b}").json()
    detail_a = client.get(f"/api/v1/runs/{run_a}").json()
    plan = detail.get("incremental") or {}
    compare = client.get(f"/api/v1/runs/{run_a}/compare/{run_b}").json()

    summary = {
        "project": pid,
        "run_a": {
            "id": run_a,
            "audited": detail_a["functions_audited"],
            "findings": detail_a["findings"],
        },
        "run_b": {
            "id": run_b,
            "mode": detail["mode"],
            "extracted": detail["functions_extracted"],
            "audited": detail["functions_audited"],
            "unchanged": detail["functions_unchanged"],
            "findings": detail["findings"],
            "plan": plan.get("files"),
            "missing": plan.get("missing"),
        },
        "compare": compare["counts"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    ok = (
        detail["functions_audited"] == 1
        and detail["functions_unchanged"] == detail["functions_extracted"] - 1
        and plan.get("missing") == []
        and plan.get("files", [{}])[0].get("changed") == ["withdraw"]
    )
    print("CI_SIMULATION:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
