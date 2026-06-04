"""LLM client supporting OpenAI, Anthropic, and local providers.

2.11: Anthropic provider now reads LLM_BASE_URL env var.
4.21: Added logging.
"""

import logging
import os

import httpx

logger = logging.getLogger("solidiguard.services.llm_client")


def chat_completion(messages: list[dict], temperature: float = 0.2) -> str:
    provider = os.environ.get("LLM_PROVIDER", "openai")
    api_key = os.environ["LLM_API_KEY"]
    model = os.environ["LLM_MODEL_NAME"]

    if provider == "openai":
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    if provider == "anthropic":
        # 2.11: Support custom base_url for Anthropic
        base_url = os.environ.get("LLM_BASE_URL", "https://api.anthropic.com/v1")
        system = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        body: dict = {
            "model": model,
            "messages": api_messages,
            "max_tokens": 4096,
            "temperature": temperature,
        }
        if system:
            body["system"] = system

        resp = httpx.post(
            f"{base_url}/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    if provider == "local":
        base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    raise ValueError(f"Unknown LLM provider: {provider}")
