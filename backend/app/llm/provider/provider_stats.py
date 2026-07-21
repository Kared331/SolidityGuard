from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict


@dataclass
class ProviderMetrics:
    provider_name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: int = 0
    total_tokens_used: int = 0
    retry_count: int = 0
    circuit_breaker_trips: int = 0
    last_error: Optional[str] = None

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_calls, 1)


class LLMObservability:
    """Records LLM call metrics for observability."""

    def __init__(self):
        self._metrics: dict[str, ProviderMetrics] = defaultdict(
            lambda: ProviderMetrics(provider_name="")
        )

    def record_call(
        self,
        provider: str,
        model: str,
        latency_ms: int,
        success: bool,
        tokens: int,
        error: Optional[str] = None,
    ):
        m = self._metrics[provider]
        m.provider_name = provider
        m.total_calls += 1
        m.total_latency_ms += latency_ms
        m.total_tokens_used += tokens
        if success:
            m.success_count += 1
        else:
            m.failure_count += 1
            m.last_error = error

    def record_retry(self, provider: str):
        self._metrics[provider].retry_count += 1

    def record_circuit_breaker(self, provider: str):
        self._metrics[provider].circuit_breaker_trips += 1

    def get_metrics(self, provider: str) -> ProviderMetrics:
        return self._metrics.get(provider, ProviderMetrics(provider_name=provider))

    def health_summary(self) -> dict:
        return {
            name: {
                "total_calls": m.total_calls,
                "success_rate": round(m.success_rate, 3),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "total_tokens": m.total_tokens_used,
                "last_error": m.last_error,
            }
            for name, m in self._metrics.items()
        }


llm_observability = LLMObservability()
