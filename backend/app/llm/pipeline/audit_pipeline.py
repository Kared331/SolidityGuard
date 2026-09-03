"""
LLM Audit Pipeline — orchestrates the full smart contract audit flow.
Breakdown: Parse → Summarize → Extract Functions → For each function: Embed → RAG Retrieve → Audit → Validate

架构状态：下一代异步 pipeline，当前未被生产路径调用。
生产路径：app.services.engine.llm_audit.LLMAuditEngine（同步 Celery 任务）
迁移计划：见 llm/pipeline/__init__.py 模块文档
"""

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass

from app.services.embedding import get_embedding

from ..budget.token_budget import token_budget
from ..prompts.registry import prompt_registry
from ..provider.base import AbstractLLMProvider
from ..provider.provider_registry import get_provider_registry
from ..rag.retriever import vulnerability_retriever
from ..schemas.prompt_context import FunctionContext
from ..security.input_sanitizer import input_sanitizer
from ..security.output_validator import output_validator

logger = logging.getLogger(__name__)


@dataclass
class AuditProgress:
    """Progress tracking for SSE streaming."""

    phase: str  # 'parsing' | 'summarizing' | 'embedding' | 'rag_retrieval' | 'auditing' | 'complete'
    current_file: str | None = None
    current_function: str | None = None
    total_functions: int = 0
    completed_functions: int = 0
    findings_so_far: int = 0


class AuditPipeline:
    def __init__(self, provider: AbstractLLMProvider | None = None):
        self._provider = provider

    @property
    def provider(self) -> AbstractLLMProvider:
        if self._provider is None:
            self._provider = get_provider_registry().get()
        return self._provider

    async def audit_contract(
        self,
        project_id: int,
        contract_name: str,
        source_code: str,
        progress_callback: callable | None = None,
    ) -> list[dict]:
        """Run full audit pipeline on a single contract."""
        findings: list[dict] = []

        # Phase 1: Sanitize
        self._emit_progress(progress_callback, AuditProgress(phase="parsing", current_file=contract_name))
        clean_code, warnings = input_sanitizer.sanitize(source_code)
        if warnings:
            logger.warning("Injection warnings for %s: %s", contract_name, warnings)

        # Phase 2: Generate contract summary
        self._emit_progress(progress_callback, AuditProgress(phase="summarizing", current_file=contract_name))
        summary_text = await self._generate_summary(contract_name, clean_code)

        # Phase 3: Extract and audit each public/external function
        functions = self._extract_functions(clean_code)
        total = len(functions)
        if total == 0:
            logger.info("No public/external functions found in %s", contract_name)
            return findings

        for i, func in enumerate(functions):
            self._emit_progress(
                progress_callback,
                AuditProgress(
                    phase="auditing",
                    current_file=contract_name,
                    current_function=func.function_name,
                    total_functions=total,
                    completed_functions=i + 1,
                    findings_so_far=len(findings),
                ),
            )

            # RAG retrieval
            func_findings = await self._audit_function(project_id, contract_name, func, summary_text, progress_callback)
            findings.extend(func_findings)

        self._emit_progress(
            progress_callback,
            AuditProgress(
                phase="complete", total_functions=total, completed_functions=total, findings_so_far=len(findings)
            ),
        )
        return findings

    async def _generate_summary(self, contract_name: str, source_code: str) -> str:
        """Generate a structured contract summary via LLM."""
        system, user = prompt_registry.render("contract_summary", contract_code=source_code[:16000])
        budget_ok, reason = token_budget.check_budget(0)
        if not budget_ok:
            logger.warning("Token budget exceeded: %s", reason)
            return json.dumps({"contract_name": contract_name, "functions": []})

        try:
            response = await self.provider.chat_completion(system, user, temperature=0.1, max_tokens=2048)
            token_budget.record_usage(0, response.usage.get("total_tokens", 0))
            return response.content
        except Exception as e:
            logger.error("Summary generation failed for %s: %s", contract_name, e)
            return json.dumps({"contract_name": contract_name, "functions": []})

    async def _audit_function(
        self,
        project_id: int,
        contract_name: str,
        func: FunctionContext,
        summary_text: str,
        progress_callback: callable | None = None,
    ) -> list[dict]:
        """Audit a single function with RAG context."""
        budget_ok, reason = token_budget.check_budget(project_id)
        if not budget_ok:
            logger.warning("Budget exceeded for project %d: %s", project_id, reason)
            return []

        # RAG retrieval: Embed function code → Query ChromaDB → Format context
        rag_context = "No similar vulnerability patterns found in knowledge base."
        try:
            self._emit_progress(
                progress_callback,
                AuditProgress(phase="embedding", current_file=contract_name, current_function=func.function_name),
            )
            embedding_text = f"// Contract: {contract_name}\n{func.function_code}"
            embedding = await asyncio.to_thread(get_embedding, embedding_text)

            self._emit_progress(
                progress_callback,
                AuditProgress(phase="rag_retrieval", current_file=contract_name, current_function=func.function_name),
            )
            results = await asyncio.to_thread(vulnerability_retriever.query, embedding)
            rag_context = vulnerability_retriever.format_rag_context(results)
            logger.debug("RAG context for %s.%s: %d chars", contract_name, func.function_name, len(rag_context))
        except Exception as e:
            logger.warning("RAG retrieval failed for %s.%s: %s", contract_name, func.function_name, e)

        # Build prompt
        system, user = prompt_registry.render(
            "function_audit",
            contract_summary=summary_text,
            function_code=func.function_code,
            rag_context=rag_context,
        )

        # Call LLM
        try:
            response = await self.provider.chat_completion(system, user)
            token_budget.record_usage(project_id, response.usage.get("total_tokens", 0))

            # Validate output
            validated = output_validator.validate_findings(response.content)
            for f in validated:
                f["contract_name"] = contract_name
                f["function_name"] = func.function_name
            return validated
        except Exception as e:
            logger.error("Audit failed for %s.%s: %s", contract_name, func.function_name, e)
            return []

    def _extract_functions(self, source_code: str) -> list[FunctionContext]:
        """Extract public/external functions using regex (fallback until AST extractor is ready)."""
        import re

        functions = []
        pattern = r"function\s+(\w+)\s*\([^)]*\)\s*(public|external)\s*([^{]*)\{([^}]*)\}"
        matches = re.findall(pattern, source_code, re.DOTALL)

        for match in matches:
            name, visibility, modifiers_str, body = match
            # Build full function text
            full_func = f"function {name}(...) {visibility} {modifiers_str}{{ {body[:3000]} }}"

            # Extract modifiers
            modifier_pattern = r"\b(onlyOwner|onlyRole|whenNotPaused|nonReentrant|initializer)\b"
            modifiers = re.findall(modifier_pattern, modifiers_str)

            functions.append(
                FunctionContext(
                    function_name=name,
                    function_code=full_func,
                    modifiers=modifiers,
                    visibility=visibility,
                )
            )

        return functions

    @staticmethod
    def _emit_progress(callback, progress: AuditProgress):
        if callback:
            with contextlib.suppress(Exception):
                callback(progress)


audit_pipeline = AuditPipeline()
