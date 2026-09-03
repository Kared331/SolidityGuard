import threading
from collections import defaultdict
from dataclasses import dataclass


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
    last_error: str | None = None

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_calls, 1)


class LLMObservability:
    """Records LLM call metrics for observability.

    P2-1: _metrics 为模块级 dict，Celery ThreadPoolExecutor 线程并发写计数非原子；
    所有读写方法在 threading.Lock 内保证计数可靠（与 token_budget A4 同模式）。
    进程内语义（E7），多 worker 部署时需换 Redis 计数器。
    """

    def __init__(self):
        self._metrics: dict[str, ProviderMetrics] = defaultdict(lambda: ProviderMetrics(provider_name=""))
        self._lock = threading.Lock()

    def record_call(
        self,
        provider: str,
        model: str,
        latency_ms: int,
        success: bool,
        tokens: int,
        error: str | None = None,
    ):
        with self._lock:
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
        with self._lock:
            self._metrics[provider].retry_count += 1

    def record_circuit_breaker(self, provider: str):
        with self._lock:
            self._metrics[provider].circuit_breaker_trips += 1

    def get_metrics(self, provider: str) -> ProviderMetrics:
        # 读也加锁，保证快照一致性（避免读到半写状态）
        with self._lock:
            m = self._metrics.get(provider, ProviderMetrics(provider_name=provider))
            # 返回副本，避免外部修改内部状态
            return ProviderMetrics(
                provider_name=m.provider_name,
                total_calls=m.total_calls,
                success_count=m.success_count,
                failure_count=m.failure_count,
                total_latency_ms=m.total_latency_ms,
                total_tokens_used=m.total_tokens_used,
                retry_count=m.retry_count,
                circuit_breaker_trips=m.circuit_breaker_trips,
                last_error=m.last_error,
            )

    def health_summary(self) -> dict:
        with self._lock:
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
