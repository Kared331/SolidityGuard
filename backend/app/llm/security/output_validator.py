"""Validates LLM JSON output against Pydantic schemas."""
from typing import Optional
from ..schemas.audit_output import AuditFindingSchema
import json


class OutputValidator:
    @staticmethod
    def validate_findings(raw_output: str) -> list[dict]:
        """Parse and validate LLM JSON output. Returns validated findings."""
        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError:
            return []

        if not isinstance(data, list):
            return []

        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                AuditFindingSchema(**item)
                validated.append(item)
            except Exception:
                continue
        return validated


output_validator = OutputValidator()
