import logging
from typing import Any

import httpx

from ..config import ProviderConfig
from .base import AbstractLLMProvider, LLMResponse

logger = logging.getLogger("solidguard.llm.provider.openai")


class OpenAIProvider(AbstractLLMProvider):
    """OpenAI-compatible LLM Provider.

    支持任何兼容 OpenAI Chat Completions API 的服务端点，
    包括 OpenAI、DeepSeek、Moonshot、vLLM 等。
    """

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._base_url = config.baseUrl.rstrip("/")
        self._api_key = config.apiKey
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        logger.info(
            "OpenAIProvider 已初始化: baseUrl=%s, models=%s",
            self._base_url,
            [m.id for m in config.models],
        )

    def _resolve_model(self) -> str:
        """返回当前配置的第一个模型 id。"""
        if self._config.models:
            return self._config.models[0].id
        return self._config.defaultModel

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        model_id = self._resolve_model()
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.debug("发送 chat completion 请求: model=%s, max_tokens=%d", model_id, max_tokens)

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        logger.info(
            "chat completion 完成: model=%s, prompt_tokens=%s, completion_tokens=%s",
            model_id,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )

        return LLMResponse(
            content=content,
            model=data.get("model", model_id),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )

    def get_model_name(self) -> str:
        return self._resolve_model()

    def health_check(self) -> bool:
        try:
            model_id = self._resolve_model()
            logger.debug("执行健康检查: baseUrl=%s, model=%s", self._base_url, model_id)
            with httpx.Client(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            ) as sync_client:
                response = sync_client.post(
                    "/chat/completions",
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                )
            ok = response.status_code == 200
            logger.info("健康检查结果: %s (status=%d)", "通过" if ok else "失败", response.status_code)
            return ok
        except Exception as exc:
            logger.warning("健康检查异常: %s", exc)
            return False

    async def close(self) -> None:
        """关闭底层 HTTP 客户端。"""
        await self._client.aclose()
        logger.info("OpenAIProvider HTTP 客户端已关闭")
