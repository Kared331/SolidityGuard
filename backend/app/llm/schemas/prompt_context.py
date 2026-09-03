"""
Structured context passed to Prompt templates during audit execution.
"""

from dataclasses import dataclass, field


@dataclass
class ContractContext:
    """Context about the contract being audited."""

    contract_name: str
    source_code: str
    lines_of_code: int = 0
    summary_json: str | None = None  # JSON string of contract summary


@dataclass
class FunctionContext:
    """Context for a single function being audited."""

    function_name: str
    function_code: str
    modifiers: list[str] = field(default_factory=list)
    visibility: str = "public"
    # RAG retrieval results
    rag_context: str = ""  # Formatted string of similar vulnerability patterns


@dataclass
class AuditContext:
    """Complete audit context for a single contract."""

    project_id: int
    contract: ContractContext
    functions: list[FunctionContext] = field(default_factory=list)
