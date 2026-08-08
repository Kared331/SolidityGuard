"""Token budget manager for LLM cost control.

Per-project token limits, configurable via solidguard.json.

线程安全：使用 threading.Lock 保护 _usage 字典，支持 ThreadPoolExecutor
文件级并行审计场景下的并发 check_budget / record_usage 调用。
"""
from __future__ import annotations

import threading
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
        self._lock = threading.Lock()

    def check_budget(self, project_id: int) -> tuple[bool, Optional[str]]:
        with self._lock:
            usage = self._usage.get(project_id, {"tokens": 0, "calls": 0})
            if usage["calls"] >= self.max_calls:
                return False, f"Max calls ({self.max_calls}) exceeded"
            if usage["tokens"] >= self.max_tokens:
                return False, f"Token budget ({self.max_tokens}) exceeded"
            return True, None

    def record_usage(self, project_id: int, tokens: int):
        with self._lock:
            if project_id not in self._usage:
                self._usage[project_id] = {"tokens": 0, "calls": 0}
            self._usage[project_id]["tokens"] += tokens
            self._usage[project_id]["calls"] += 1

    def get_usage(self, project_id: int) -> dict:
        with self._lock:
            return self._usage.get(project_id, {"tokens": 0, "calls": 0})

    def reset(self, project_id: int):
        with self._lock:
            self._usage.pop(project_id, None)


token_budget = TokenBudget()
