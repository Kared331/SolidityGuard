"""Anthropic Messages API LLM Provider 实现。

通过 Anthropic Messages API 发送聊天请求，兼容 Claude 系列模型。
"""

import logging

import httpx

from .base import AbstractLLMProvider, LLMResponse, llm_retry
from ..config import ProviderConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(AbstractLLMProvider):
    """Anthropic Messages API 的 LLM Provider 实现。"""

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._api_key = config.apiKey
        self._base_url = config.baseUrl.rstrip("/")
        self._default_model = config.defaultModel

    def _get_model_id(self) -> str:
        """获取当前模型 ID，优先使用 defaultModel，否则使用第一个模型。"""
        if self._default_model:
            return self._default_model
        if self._config.models:
            return self._config.models[0].id
        raise ValueError("AnthropicProvider 没有配置任何模型")

    @llm_retry(logger, "anthropic")
    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """调用 Anthropic Messages API 发送聊天请求。"""
        model_id = self._get_model_id()
        url = f"{self._base_url}/messages"

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }

        logger.debug("Anthropic 请求: model=%s, max_tokens=%d", model_id, max_tokens)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        usage = data["usage"]

        result = LLMResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            usage={
                "prompt_tokens": usage["input_tokens"],
                "completion_tokens": usage["output_tokens"],
                "total_tokens": usage["input_tokens"] + usage["output_tokens"],
            },
        )

        logger.debug(
            "Anthropic 响应: tokens=%d", result.usage["total_tokens"]
        )
        return result

    def get_model_name(self) -> str:
        """返回当前配置的模型 ID。"""
        return self._get_model_id()

    def health_check(self) -> bool:
        """检测 Anthropic API 可用性。

        使用同步 httpx.Client 发送最小化请求验证连通性。
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self._base_url}/messages",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._get_model_id(),
                        "max_tokens": 1,
                        "messages": [
                            {"role": "user", "content": "ping"}
                        ],
                    },
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("Anthropic health_check 失败: %s", e)
            return False
