from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


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
    error: Optional[str] = None


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
