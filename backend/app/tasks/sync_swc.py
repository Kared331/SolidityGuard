"""SWC knowledge sync with GitHub API auth (4.16) and error handling (4.14)."""

import logging
import os
import re

import httpx
from celery import shared_task

from app.database import get_sync_session
from app.models import VulnerabilityEntry
from app.services.chroma_client import get_vulnerability_collection
from app.services.embedding import get_embedding

logger = logging.getLogger("solidiguard.tasks.sync_swc")


@shared_task(name="app.tasks.sync_swc.sync_swc", bind=True)
def sync_swc(self):
    try:
        # 4.16: Support GitHub token for higher rate limits
        github_token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
            logger.info("Using authenticated GitHub API request")
        else:
            logger.warning(
                "No GITHUB_TOKEN set – GitHub API rate limit is 60 req/hour. "
                "Set GITHUB_TOKEN env var for higher limits."
            )

        # Step 1: Fetch SWC entries from GitHub API
        resp = httpx.get(
            "https://api.github.com/repos/SmartContractSecurity/SWC-registry/contents/entries/docs",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        entries = [e for e in resp.json() if re.match(r"^SWC-\d+\.md$", e["name"])]

        # Step 2: Parse and upsert entries into database
        with get_sync_session() as session:
            for entry_meta in entries:
                name = entry_meta["name"]
                swc_id = name.replace(".md", "").upper()

                # Fetch raw markdown content
                file_resp = httpx.get(
                    entry_meta["url"],
                    headers={"Accept": "application/vnd.github.v3.raw"},
                    timeout=30,
                )
                file_resp.raise_for_status()
                raw_content = file_resp.text

                # Parse markdown: title
                title_match = re.search(r"^#\s+(.+)", raw_content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else swc_id

                # Parse markdown: description section
                desc_match = re.search(
                    r"##\s+Description\s*\n(.*?)(?=\n##|\Z)", raw_content, re.DOTALL
                )
                description = desc_match.group(1).strip() if desc_match else ""

                # Parse markdown: first Solidity code example
                code_match = re.search(r"```solidity\s*\n(.*?)```", raw_content, re.DOTALL)
                code_example = code_match.group(1).strip() if code_match else None

                # Parse markdown: severity (if present)
                severity_match = re.search(
                    r"(?:Severity|Severity Level)\s*:\s*(\w+)", raw_content, re.IGNORECASE
                )
                severity = severity_match.group(1) if severity_match else None

                # Upsert into database
                existing = session.query(VulnerabilityEntry).filter_by(swc_id=swc_id).first()
                if existing:
                    existing.title = title
                    existing.description = description
                    existing.severity = severity
                    existing.code_example = code_example
                else:
                    session.add(
                        VulnerabilityEntry(
                            swc_id=swc_id,
                            title=title,
                            description=description,
                            severity=severity,
                            code_example=code_example,
                        )
                    )

            session.commit()

        # Step 3: Generate embeddings and store in Chroma
        with get_sync_session() as session:
            vuln_entries = session.query(VulnerabilityEntry).all()
            collection = get_vulnerability_collection()

            for vuln in vuln_entries:
                parts = [vuln.title, vuln.description]
                if vuln.code_example:
                    parts.append(vuln.code_example)
                text = "\n\n".join(parts)

                try:
                    embedding = get_embedding(text)
                except Exception:
                    logger.warning("Failed to generate embedding for %s", vuln.swc_id)
                    continue

                collection.upsert(
                    ids=[vuln.swc_id],
                    documents=[text],
                    embeddings=[embedding],
                )

        logger.info("SWC sync completed: %d entries synced", len(entries))
        return {"status": "completed", "entries_synced": len(entries)}

    except Exception:
        logger.exception("SWC sync failed")
        self.update_state(state="FAILURE", meta={"exc": str(Exception)})
        raise
