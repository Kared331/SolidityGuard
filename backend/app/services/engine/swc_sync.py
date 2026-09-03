import os
import re

import httpx

from app.services.engine.base import BaseEngine


# SWC Registry 官方标题（https://swcregistry.io，2018 定稿后保持稳定）。
# 上游仓库（SmartContractSecurity/SWC-registry）已于 2020 年后归档，所有
# SWC-*.md 被替换为弃用横幅 + "# Title" 占位，正文无真实标题，故此处内置
# 官方标准名称做覆盖，Description/代码示例仍从上游正文解析。
_SWC_TITLES = {
    "SWC-100": "Function Default Visibility",
    "SWC-101": "Integer Overflow and Underflow",
    "SWC-102": "Outdated Compiler Version",
    "SWC-103": "Floating Pragma",
    "SWC-104": "Unchecked Call Return Value",
    "SWC-105": "Unprotected Ether Withdrawal",
    "SWC-106": "Unprotected SELFDESTRUCT Instruction",
    "SWC-107": "Reentrancy",
    "SWC-108": "State Variable Default Visibility",
    "SWC-109": "Uninitialized Storage Pointer",
    "SWC-110": "Assert Violation",
    "SWC-111": "Use of Deprecated Solidity Functions",
    "SWC-112": "Delegatecall to Untrusted Callee",
    "SWC-113": "DoS with Failed Call",
    "SWC-114": "Transaction Order Dependence",
    "SWC-115": "Authorization through tx.origin",
    "SWC-116": "Block values as a proxy for time",
    "SWC-117": "Signature Malleability",
    "SWC-118": "Incorrect Constructor Name",
    "SWC-119": "Shadowing State Variables",
    "SWC-120": "Weak Sources of Randomness from Chain Attributes",
    "SWC-121": "Missing Protection against Signature Replay Attacks",
    "SWC-122": "Missing Input Validation",
    "SWC-123": "Requirement Violation",
    "SWC-124": "Write to Arbitrary Storage Location",
    "SWC-125": "Incorrect Inheritance Order",
    "SWC-126": "Insufficient Gas Griefing",
    "SWC-127": "Arbitrary Jump with Function Type Variable",
    "SWC-128": "DoS With Block Gas Limit",
    "SWC-129": "Typographical Error",
    "SWC-130": "Right-To-Left-Override control character (U+202E)",
    "SWC-131": "Presence of unused variables",
    "SWC-132": "Unexpected Ether balance",
    "SWC-133": "Hash Collisions With Multiple Variable Length Arguments",
    "SWC-134": "Message call with hardcoded gas amount",
    "SWC-135": "Code With No Effects",
    "SWC-136": "Uninitialized Local Variables",
}

# 上游仓库在 2020 后插入的弃用横幅（每个文件开头第一个 H1），解析时需跳过
_DEPRECATED_BANNER = re.compile(
    r"^#\s+Please note, this content is no longer actively maintained\.",
    re.MULTILINE,
)


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


def _parse_swc_markdown(raw_content: str, swc_id: str | None = None) -> dict:
    """Parse SWC markdown content into structured data.

    标题优先用内置官方映射（上游仓库已归档，正文标题被弃用横幅与
    "# Title" 占位符取代）；映射缺失时回退到解析第一个非横幅 H1。
    """
    title = _SWC_TITLES.get(swc_id or "") if swc_id else None
    if not title:
        title_match = re.search(
            r"^#\s+(.+)", _DEPRECATED_BANNER.sub("", raw_content), re.MULTILINE
        )
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

            file_headers = {"Accept": "application/vnd.github.v3.raw"}
            if github_token:
                file_headers["Authorization"] = f"token {github_token}"

            file_resp = httpx.get(
                entry_meta["url"],
                headers=file_headers,
                timeout=30,
            )
            file_resp.raise_for_status()
            raw_content = file_resp.text

            parsed = _parse_swc_markdown(raw_content, swc_id)
            parsed["swc_id"] = swc_id
            parsed_entries.append(parsed)

        return {
            "entries_synced": len(parsed_entries),
            "parsed_entries": parsed_entries,
        }
