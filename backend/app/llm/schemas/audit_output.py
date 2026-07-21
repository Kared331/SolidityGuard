"""
Pydantic schemas for LLM audit output validation.
Used to validate and parse LLM JSON responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class AuditFindingSchema(BaseModel):
    """Schema for a single audit finding from LLM output."""

    vulnerability_description: str = Field(
        ..., description="Detailed explanation of the vulnerability"
    )
    severity: Literal["Critical", "High", "Medium", "Low", "Informational"] = Field(
        ..., description="Vulnerability severity level"
    )
    impact: str = Field(
        ..., description="Concrete description of what an attacker could achieve"
    )
    suggested_fix: str = Field(
        ..., description="Specific code changes to fix the vulnerability"
    )
    gas_optimization: Optional[str] = Field(
        None, description="Optional gas optimization suggestion"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0"
    )


class ContractSummarySchema(BaseModel):
    """Schema for LLM-generated contract summary."""

    contract_name: str
    inheritance: list[str] = Field(default_factory=list)
    state_variables: list[dict] = Field(default_factory=list)
    functions: list[dict] = Field(default_factory=list)
    security_patterns: list[str] = Field(default_factory=list)
    lines_of_code: int = 0


class AuditBatchResult(BaseModel):
    """Batch of audit findings from a single function audit."""

    function_name: str
    contract_name: str
    findings: list[AuditFindingSchema] = Field(default_factory=list)
    error: Optional[str] = None
