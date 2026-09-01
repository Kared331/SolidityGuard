"""Token budget manager for LLM cost control.

Per-project token limits, configurable via solidguard.json.

线程安全：使用 threading.Lock 保护 _usage 字典，支持 ThreadPoolExecutor
文件级并行审计场景下的并发 check_budget / record_usage 调用。

P1-7 (S1): 预算持久化。
    原 _usage 为进程内 dict，worker 重启即清零，预算上限对「重启后的
    累计消耗」失效。现增加任务级落库：run_llm_audit 结束时调用
    persist_usage 将本项目累计写入 Redis（键 solidguard:token_usage:<pid>）；
    TokenBudget 在 worker 启动初始化时从 Redis 载入既有累计值，使
    check_budget 基线包含历史消耗。不做逐调用写库（避免写入放大）。
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Optional

from app.config import settings

logger = logging.getLogger("solidguard.llm.budget")

_USAGE_KEY_PREFIX = "solidguard:token_usage:"


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

    # ── P1-7: 持久化（Redis 任务级落库） ────────────────────────

    def persist_usage(self, project_id: int) -> None:
        """将本项目累计 usage 写入 Redis（任务结束时调用）。

        不做逐调用写库——避免写入放大，任务内存累计 + 结束一次性写入即可。
        约束 A4：persist 在锁内读取快照，锁外执行 Redis IO（不持锁等待网络）。
        """
        with self._lock:
            snapshot = dict(self._usage.get(project_id, {"tokens": 0, "calls": 0}))

        try:
            import redis

            r = redis.from_url(settings.REDIS_URL, socket_timeout=2)
            r.setex(
                f"{_USAGE_KEY_PREFIX}{project_id}",
                86400 * 30,  # 30 天 TTL，超过清理周期自动过期
                json.dumps(snapshot),
            )
            r.close()
        except Exception as exc:
            logger.warning("Token usage 持久化失败 (project_id=%d): %s", project_id, exc)

    def load_usage(self, project_id: int) -> None:
        """从 Redis 载入本项目既有累计 usage（worker 启动初始化时调用）。

        载入仅发生在 TokenBudget 初始化（worker 启动）时，运行中不重复载入；
        合并到 _usage 基线，使 check_budget 包含重启前累计（A4 锁保护合并）。
        """
        try:
            import redis

            r = redis.from_url(settings.REDIS_URL, socket_timeout=2)
            raw = r.get(f"{_USAGE_KEY_PREFIX}{project_id}")
            r.close()
            if raw is None:
                return
            persisted = json.loads(raw)
            with self._lock:
                current = self._usage.get(project_id, {"tokens": 0, "calls": 0})
                # 取 max 确保不回退（防止载入旧值覆盖新累计）
                self._usage[project_id] = {
                    "tokens": max(current["tokens"], persisted.get("tokens", 0)),
                    "calls": max(current["calls"], persisted.get("calls", 0)),
                }
            logger.info(
                "Token usage 已从 Redis 载入 (project_id=%d): tokens=%d, calls=%d",
                project_id,
                self._usage[project_id]["tokens"],
                self._usage[project_id]["calls"],
            )
        except Exception as exc:
            logger.debug("Token usage 载入跳过 (project_id=%d): %s", project_id, exc)


token_budget = TokenBudget()
