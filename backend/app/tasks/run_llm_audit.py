"""LLM audit task with improved function extraction (2.10) and error handling (4.14)."""

import json
import logging
import os
import re

from app.celery_app import celery
from app.database import get_sync_session
from app.models import LLMAuditResult, ProjectFile
from app.services.chroma_client import get_vulnerability_collection
from app.services.embedding import get_embedding
from app.services.llm_client import chat_completion

logger = logging.getLogger("solidiguard.tasks.run_llm_audit")


def _extract_key_functions(source_code: str) -> list[dict]:
    """Extract public/external functions with their bodies (2.10: robust regex).

    Supports:
    - Multi-line declarations
    - Modifiers (public, external, view, pure, etc.)
    - Returns clauses
    - Function names with underscores, numbers
    """
    results = []

    # Find all function declarations (2.10: handles modifiers, returns, multiline)
    pattern = r"function\s+(\w+)\s*\([^)]*\)[^{]*?\{"
    for match in re.finditer(pattern, source_code, re.DOTALL):
        func_name = match.group(1)

        # Skip constructor, receive, fallback
        if func_name in ("constructor", "receive", "fallback"):
            continue

        # Extract function body by counting braces
        start = match.end() - 1
        depth = 1
        i = start + 1
        while i < len(source_code) and depth > 0:
            if source_code[i] == "{":
                depth += 1
            elif source_code[i] == "}":
                depth -= 1
            i += 1
        func_body = source_code[start:i]

        # Only audit functions that interact with ETH/token
        keywords = [
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
        ]
        if any(kw in func_body for kw in keywords):
            results.append({"name": func_name, "body": func_body})

    return results


@celery.task(name="run_llm_audit", bind=True)
def run_llm_audit(self, project_id: int) -> None:
    try:
        with get_sync_session() as session:
            files = (
                session.query(ProjectFile)
                .filter(ProjectFile.project_id == project_id)
                .all()
            )

            for pf in files:
                file_path = os.path.join("uploads", str(project_id), pf.file_path)
                if not os.path.isfile(file_path):
                    continue
                if not pf.file_path.endswith(".sol"):
                    continue

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                contract_name = os.path.basename(pf.file_path)

                # Generate contract summary
                summary_messages = [
                    {
                        "role": "user",
                        "content": (
                            f'Analyze this Solidity contract and provide a structured summary with: '
                            f'1) interface description, 2) state variables, '
                            f'3) function signatures and descriptions.\n\n'
                            f"Contract:\n{content}\n\n"
                            f'Output JSON: {{"interface": "...", "state_variables": [...], '
                            f'"functions": [...]}}'
                        ),
                    }
                ]
                try:
                    summary_text = chat_completion(summary_messages)
                except Exception:
                    logger.warning("Failed to generate summary for %s", contract_name)
                    continue

                key_functions = _extract_key_functions(content)
                collection = get_vulnerability_collection()

                for func in key_functions:
                    try:
                        embedding = get_embedding(func["body"])
                    except Exception:
                        logger.warning(
                            "Failed to get embedding for %s.%s",
                            contract_name,
                            func["name"],
                        )
                        continue

                    try:
                        query_results = collection.query(
                            query_embeddings=[embedding],
                            n_results=int(os.environ.get("RAG_TOP_K", 5)),
                        )
                    except Exception:
                        logger.warning("ChromaDB query failed for %s.%s", contract_name, func["name"])
                        query_results = {"documents": [[]], "metadatas": [[]]}

                    retrieved_docs = query_results.get("documents", [[]])[0]
                    retrieved_metas = query_results.get("metadatas", [[]])[0]

                    vuln_texts = []
                    for doc, meta in zip(retrieved_docs, retrieved_metas):
                        title = meta.get("title", "Unknown") if meta else "Unknown"
                        vuln_texts.append(f"- {title}: {doc}")
                    retrieved_vulnerabilities = "\n".join(vuln_texts) or "None found"

                    audit_messages = [
                        {
                            "role": "user",
                            "content": (
                                f"You are a Solidity security auditor.\n\n"
                                f"Contract Summary:\n{summary_text}\n\n"
                                f"Function to audit:\n{func['body']}\n\n"
                                f"Similar vulnerabilities found via RAG:\n"
                                f"{retrieved_vulnerabilities}\n\n"
                                f"Identify vulnerabilities, severity, suggested fixes, "
                                f"and gas optimizations for this function.\n"
                                f'Return a JSON array of objects: [{{"vulnerability_description": "...", '
                                f'"severity": "...", "suggested_fix": "...", '
                                f'"gas_optimization": "..."}}]'
                            ),
                        }
                    ]

                    try:
                        response_text = chat_completion(audit_messages)
                        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
                        if not json_match:
                            continue
                        findings = json.loads(json_match.group())
                    except (json.JSONDecodeError, Exception):
                        logger.warning(
                            "Failed to parse LLM audit response for %s.%s",
                            contract_name,
                            func["name"],
                        )
                        continue

                    for finding in findings:
                        session.add(
                            LLMAuditResult(
                                project_id=project_id,
                                contract_name=contract_name,
                                function_name=func["name"],
                                vulnerability_description=finding.get(
                                    "vulnerability_description", ""
                                ),
                                severity=finding.get("severity", "unknown"),
                                suggested_fix=finding.get("suggested_fix"),
                                gas_optimization=finding.get("gas_optimization"),
                            )
                        )

            session.commit()
            logger.info("LLM audit completed for project %d", project_id)

    except Exception:
        logger.exception("LLM audit failed for project %d", project_id)
        self.update_state(state="FAILURE", meta={"exc": str(Exception)})
        raise
