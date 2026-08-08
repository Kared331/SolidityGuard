"""同步包装器：桥接异步 LLM Provider 与同步调用方（如 Celery 任务）。"""
from __future__ import annotations

import asyncio
import logging
from typing import Tuple

logger = logging.getLogger("solidguard.llm.sync_wrapper")


def chat_completion(
    messages: list[dict], temperature: float = 0.2
) -> Tuple[str, dict]:
    """同步版聊天补全接口。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 采样温度

    Returns:
        (response_content, usage_dict)
    """
    from .provider.provider_registry import get_provider_registry

    registry = get_provider_registry()
    provider = registry.get()

    system_prompt = ""
    user_parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            user_parts.append(content)

    user_prompt = "\n".join(user_parts) if user_parts else ""

    async def _call():
        response = await provider.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        return response.content, response.usage

    return asyncio.run(_call())
