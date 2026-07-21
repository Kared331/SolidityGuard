"""LLM 客户端，基于配置文件路由到对应的 API 适配器。

从 solidguard.json 读取 Provider 配置，根据 api 字段选择调用方式：
  - "openai"             → POST {baseUrl}/chat/completions
  - "anthropic-messages" → POST {baseUrl}/messages

保留同步接口以兼容 Celery 任务等同步上下文调用方。
"""
from __future__ import annotations

import logging
from typing import Tuple

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.llm.config import get_config, ProviderConfig

logger = logging.getLogger("solidiguard.services.llm_client")

MAX_RESPONSE_TOKENS = 4096
_llm_failure_count = 0
_LLM_CIRCUIT_BREAKER_THRESHOLD = 5
_client = httpx.Client(timeout=120)


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _get_default_provider_config() -> ProviderConfig:
    """从配置文件获取默认 Provider 配置。"""
    config = get_config()
    return config.get_default_provider()


def _extract_prompts(messages: list[dict]) -> Tuple[str, str]:
    """从 OpenAI 格式的 messages 列表中提取 system_prompt 和 user_prompt。

    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = ""
    user_parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            user_parts.append(content)
        elif role == "assistant":
            # 将 assistant 消息也保留在 user_parts 中，供部分 Provider 使用
            user_parts.append(f"[Assistant]: {content}")
    user_prompt = "\n".join(user_parts) if user_parts else ""
    return system_prompt, user_prompt


def _call_openai_compatible(
    provider: ProviderConfig,
    messages: list[dict],
    temperature: float,
) -> Tuple[str, dict]:
    """调用 OpenAI 兼容 API（POST {baseUrl}/chat/completions）。"""
    base_url = provider.baseUrl.rstrip("/")
    url = f"{base_url}/chat/completions"
    model = provider.defaultModel or (provider.models[0].id if provider.models else "")
    max_tokens = provider.models[0].maxTokens if provider.models else MAX_RESPONSE_TOKENS

    headers = {
        "Authorization": f"Bearer {provider.apiKey}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    logger.debug("OpenAI 兼容请求: url=%s, model=%s", url, model)
    resp = _client.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    if not usage:
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": max_tokens,
            "total_tokens": max_tokens,
        }

    logger.info(
        "OpenAI 兼容调用完成: model=%s, prompt_tokens=%s, completion_tokens=%s",
        model,
        usage.get("prompt_tokens"),
        usage.get("completion_tokens"),
    )
    return content, usage


def _call_anthropic_messages(
    provider: ProviderConfig,
    messages: list[dict],
    temperature: float,
) -> Tuple[str, dict]:
    """调用 Anthropic Messages API（POST {baseUrl}/messages）。"""
    base_url = provider.baseUrl.rstrip("/")
    url = f"{base_url}/messages"
    model = provider.defaultModel or (provider.models[0].id if provider.models else "")
    max_tokens = provider.models[0].maxTokens if provider.models else MAX_RESPONSE_TOKENS

    headers = {
        "x-api-key": provider.apiKey,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    system_prompt, user_prompt = _extract_prompts(messages)

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }
    if system_prompt:
        payload["system"] = system_prompt

    logger.debug("Anthropic Messages 请求: url=%s, model=%s", url, model)
    resp = _client.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()

    content = data["content"][0]["text"]
    usage_raw = data.get("usage", {})
    usage = {
        "prompt_tokens": usage_raw.get("input_tokens", 0),
        "completion_tokens": usage_raw.get("output_tokens", 0),
        "total_tokens": usage_raw.get("input_tokens", 0) + usage_raw.get("output_tokens", 0),
    }

    logger.info(
        "Anthropic Messages 调用完成: model=%s, prompt_tokens=%s, completion_tokens=%s",
        model,
        usage["prompt_tokens"],
        usage["completion_tokens"],
    )
    return content, usage


# API 路由表
_API_ROUTES = {
    "openai": _call_openai_compatible,
    "anthropic-messages": _call_anthropic_messages,
}


# ---------------------------------------------------------------------------
# 公开接口（保持原有签名不变）
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (
            httpx.HTTPStatusError,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
        )
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def chat_completion(
    messages: list[dict], temperature: float = 0.2
) -> Tuple[str, dict]:
    """发送聊天补全请求。

    从配置文件读取默认 Provider，根据 api 字段路由到对应 API 适配器。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 采样温度

    Returns:
        (response_content, usage_dict)

    Raises:
        RuntimeError: 熔断器打开时
        ValueError: 未知的 api 类型时
    """
    global _llm_failure_count

    if _llm_failure_count >= _LLM_CIRCUIT_BREAKER_THRESHOLD:
        raise RuntimeError("LLM circuit breaker open")

    try:
        provider_cfg = _get_default_provider_config()
        api_type = provider_cfg.api

        handler = _API_ROUTES.get(api_type)
        if handler is None:
            raise ValueError(f"未知的 LLM api 类型: {api_type}")

        content, usage = handler(provider_cfg, messages, temperature)
        _llm_failure_count = 0
        return content, usage
    except Exception:
        _llm_failure_count += 1
        raise
