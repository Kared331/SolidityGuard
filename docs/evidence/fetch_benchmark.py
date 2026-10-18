"""Fetch the SmartBugs-curated benchmark (143 labeled vulnerable contracts).

Labels come from the dataset directory name (one category per contract).
Nothing is vendored into git: files land in `corpus/smartbugs/` (ignored).

Usage:
    python docs/evidence/fetch_benchmark.py
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "corpus" / "smartbugs"
URL = "https://codeload.github.com/smartbugs/smartbugs-curated/tar.gz/main"


def main() -> int:
    with urllib.request.urlopen(URL, timeout=120) as resp:  # noqa: S310 - fixed host
        data = resp.read()

    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)

    labels: dict[str, str] = {}
    sha = ""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        sha = (tar.pax_headers or {}).get("comment", "")
        top = tar.getmembers()[0].name.split("/")[0]

        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".sol"):
                continue
            rel = member.name[len(top) + 1 :]
            parts = rel.split("/")
            if len(parts) < 3 or parts[0] != "dataset":
                continue
            category = parts[1]
            dest = TARGET / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(tar.extractfile(member).read())
            labels[rel] = category

    (TARGET / "labels.json").write_text(
        json.dumps({"sha": sha, "labels": labels}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for category in labels.values():
        counts[category] = counts.get(category, 0) + 1
    print(f"sha={sha[:12]} contracts={len(labels)}")
    for category, count in sorted(counts.items()):
        print(f"  {category:<28} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
