"""Fetch a pinned DeFi/Solidity corpus for extraction measurement (P5).

We do NOT vendor third-party sources: this script downloads tarballs from
codeload.github.com, keeps only the .sol files matching the manifest, and
writes `corpus.lock.json` with the real commit SHA of every tarball.

The SHA comes from the tarball's pax global header (`comment`), so no GitHub
API access is needed (api.github.com may be blocked; codeload is not).

Usage:
    python docs/evidence/fetch_corpus.py            # fetch (uses lock if present)
    python docs/evidence/fetch_corpus.py --refresh  # re-resolve heads, rewrite lock
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
LOCK = Path(__file__).with_name("corpus.lock.json")

MANIFEST = [
    {
        "name": "uniswap-v2-core",
        "repo": "Uniswap/v2-core",
        "ref": "master",
        "prefixes": ["contracts/"],
    },
    {
        "name": "uniswap-v2-periphery",
        "repo": "Uniswap/v2-periphery",
        "ref": "master",
        "prefixes": ["contracts/"],
    },
    {
        "name": "compound",
        "repo": "compound-finance/compound-protocol",
        "ref": "master",
        "prefixes": ["contracts/"],
    },
    {
        "name": "openzeppelin",
        "repo": "OpenZeppelin/openzeppelin-contracts",
        "ref": "master",
        "prefixes": [
            "contracts/token/ERC20/",
            "contracts/access/",
            "contracts/proxy/",
        ],
    },
    {
        "name": "solmate",
        "repo": "transmissions11/solmate",
        "ref": "main",
        "prefixes": ["src/"],
    },
]


def _download(repo: str, ref: str) -> bytes:
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 - fixed host
        return resp.read()


def _matches(path: str, prefixes: list[str]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def fetch(entry: dict, use_locked: bool) -> dict:
    locked = {}
    if use_locked and LOCK.is_file():
        locked = {e["name"]: e for e in json.loads(LOCK.read_text(encoding="utf-8"))}

    ref = locked[entry["name"]]["sha"] if entry["name"] in locked else entry["ref"]
    data = _download(entry["repo"], ref)

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        sha = (tar.pax_headers or {}).get("comment", "")
        members = tar.getmembers()
        top = members[0].name.split("/")[0] if members else ""

        target = CORPUS / entry["name"]
        if target.exists():
            shutil.rmtree(target)

        files = []
        for member in members:
            if not member.isfile() or not member.name.endswith(".sol"):
                continue
            rel = member.name[len(top) + 1 :] if member.name.startswith(top + "/") else member.name
            if not _matches(rel, entry["prefixes"]):
                continue
            payload = tar.extractfile(member).read()
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
            files.append({"path": rel, "sha256": hashlib.sha256(payload).hexdigest()})

    return {
        "name": entry["name"],
        "repo": entry["repo"],
        "sha": sha or "unknown",
        "files": sorted(files, key=lambda f: f["path"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-resolve branch heads and rewrite the lock")
    args = ap.parse_args()

    CORPUS.mkdir(exist_ok=True)
    results = []
    for entry in MANIFEST:
        result = fetch(entry, use_locked=not args.refresh)
        results.append(result)
        print(f"{result['name']:<24} sha={result['sha'][:12]} files={len(result['files'])}")

    LOCK.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(r["files"]) for r in results)
    print(f"total files: {total}  -> {CORPUS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
