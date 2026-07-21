import os
import re

import httpx

from app.services.engine.base import BaseEngine


def _fetch_swc_entries(github_token: str) -> list[dict]:
    """Fetch SWC entries from GitHub API."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    resp = httpx.get(
        "https://api.github.com/repos/SmartContractSecurity/SWC-registry/contents/entries/docs",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    entries = [e for e in resp.json() if re.match(r"^SWC-\d+\.md$", e["name"])]
    return entries


def _parse_swc_markdown(raw_content: str) -> dict:
    """Parse SWC markdown content into structured data."""
    title_match = re.search(r"^#\s+(.+)", raw_content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else None

    desc_match = re.search(
        r"##\s+Description\s*\n(.*?)(?=\n##|\Z)", raw_content, re.DOTALL
    )
    description = desc_match.group(1).strip() if desc_match else ""

    code_match = re.search(r"```solidity\s*\n(.*?)```", raw_content, re.DOTALL)
    code_example = code_match.group(1).strip() if code_match else None

    severity_match = re.search(
        r"(?:Severity|Severity Level)\s*:\s*(\w+)", raw_content, re.IGNORECASE
    )
    severity = severity_match.group(1) if severity_match else None

    return {
        "title": title,
        "description": description,
        "severity": severity,
        "code_example": code_example,
    }


class SWCSyncEngine(BaseEngine):
    def execute(self) -> dict:
        github_token = os.environ.get("GITHUB_TOKEN", "")

        entries = _fetch_swc_entries(github_token)

        parsed_entries = []
        for entry_meta in entries:
            name = entry_meta["name"]
            swc_id = name.replace(".md", "").upper()

            file_resp = httpx.get(
                entry_meta["url"],
                headers={"Accept": "application/vnd.github.v3.raw"},
                timeout=30,
            )
            file_resp.raise_for_status()
            raw_content = file_resp.text

            parsed = _parse_swc_markdown(raw_content)
            parsed["swc_id"] = swc_id
            parsed_entries.append(parsed)

        return {
            "entries_synced": len(parsed_entries),
            "parsed_entries": parsed_entries,
        }
