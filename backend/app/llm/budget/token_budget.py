"""Token budget manager for LLM cost control.

Per-project token limits, configurable via solidguard.json.
"""

from typing import Optional

from app.config import settings


class TokenBudget:
    def __init__(
        self,
        max_tokens: int | None = None,
        max_calls: int | None = None,
    ):
        self.max_tokens = max_tokens or settings.TOKEN_BUDGET_PER_PROJECT
        self.max_calls = max_calls or settings.MAX_LLM_CALLS_PER_PROJECT
        self._usage: dict[int, dict] = {}

    def check_budget(self, project_id: int) -> tuple[bool, Optional[str]]:
        usage = self._usage.get(project_id, {"tokens": 0, "calls": 0})
        if usage["calls"] >= self.max_calls:
            return False, f"Max calls ({self.max_calls}) exceeded"
        if usage["tokens"] >= self.max_tokens:
            return False, f"Token budget ({self.max_tokens}) exceeded"
        return True, None

    def record_usage(self, project_id: int, tokens: int):
        if project_id not in self._usage:
            self._usage[project_id] = {"tokens": 0, "calls": 0}
        self._usage[project_id]["tokens"] += tokens
        self._usage[project_id]["calls"] += 1

    def get_usage(self, project_id: int) -> dict:
        return self._usage.get(project_id, {"tokens": 0, "calls": 0})

    def reset(self, project_id: int):
        self._usage.pop(project_id, None)


token_budget = TokenBudget()
