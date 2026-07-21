"""Token budget manager for LLM cost control (Sprint 3, blueprint 6.1).

Tracks token consumption and call counts per project using an
in-memory dictionary.  Single-process only; not persisted across
restarts per sprint requirements.
"""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class TokenBudgetManager:
    """Track and limit token usage per project."""

    max_tokens_per_project: int = 500_000
    max_llm_calls_per_project: int = 100
    project_usage: dict = field(
        default_factory=lambda: defaultdict(
            lambda: {"tokens": 0, "calls": 0}
        )
    )

    def check_budget(self, project_id: int) -> bool:
        """Return True if the project has budget remaining."""
        usage = self.project_usage[project_id]
        if usage["calls"] >= self.max_llm_calls_per_project:
            return False
        if usage["tokens"] >= self.max_tokens_per_project:
            return False
        return True

    def record_usage(self, project_id: int, usage: dict) -> None:
        """Record token consumption from an LLM call."""
        u = self.project_usage[project_id]
        u["calls"] += 1
        u["tokens"] += usage.get("total_tokens", 0)

    def reset_project(self, project_id: int) -> None:
        """Reset budget tracking for a project."""
        self.project_usage.pop(project_id, None)


# Module-level singleton
_budget_manager = TokenBudgetManager()


def get_budget_manager() -> TokenBudgetManager:
    return _budget_manager