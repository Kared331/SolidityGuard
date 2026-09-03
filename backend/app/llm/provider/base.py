import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("solidguard.llm.provider.base")

# 可重试的 HTTP 状态码：限流与服务端瞬时故障
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable_llm_error(exc: BaseException) -> bool:
    """判断 LLM 调用异常是否值得重试（P0-2）。

    可重试：网络连接失败、读超时、限流与服务端瞬时故障（429/5xx）。
    明确不重试：400/401/403/404/422（请求非法或凭证类错误，立即失败，
    落入既有 unknown-severity 降级路径）。
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout))


def describe_llm_error(exc: BaseException) -> str:
    """生成可区分的 LLM 失败原因描述（S4：401/429/超时可观测）。

    注意：部分网络异常（如 ConnectError）的 str(e) 可能为空，
    回退到异常类型名，保证日志与落库文案非空（S4 空 WARNING 行防线）。
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTPStatusError {exc.response.status_code}"
    if isinstance(exc, httpx.ReadTimeout):
        return "ReadTimeout"
    if isinstance(exc, httpx.ConnectError):
        return "ConnectError"
    return str(exc) or type(exc).__name__


def llm_retry(logger_: logging.Logger, provider_name: str):
    """构造 LLM chat_completion 的 tenacity 重试装饰器（P0-2）。

    复用 embedding 服务既有的重试风格（stop=3, 指数退避 2-30s）。
    重试事件经 before_sleep 输出 WARNING 日志并计入 provider_stats
    （计数完全可靠依赖 P2-1 补锁，届时一并验证）。
    """
    from .provider_stats import llm_observability

    def _before_sleep(retry_state) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        logger_.warning(
            "LLM 调用失败，即将重试（provider=%s, attempt=%d, error=%s）",
            provider_name,
            retry_state.attempt_number,
            describe_llm_error(exc) if exc is not None else "unknown",
        )
        llm_observability.record_retry(provider_name)

    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(is_retryable_llm_error),
        before_sleep=_before_sleep,
        reraise=True,
    )


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict  # {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}


@dataclass
class LLMCallRecord:
    provider: str
    model: str
    latency_ms: int
    success: bool
    tokens_used: int
    error: str | None = None


class AbstractLLMProvider(ABC):
    """Abstract base for LLM providers (OpenAI, Ollama, etc.)"""

    @abstractmethod
    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat completion request and return the LLM response."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the active model name."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is reachable and working."""
        ...
