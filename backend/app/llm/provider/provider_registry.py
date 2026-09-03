from __future__ import annotations

import logging

from .base import AbstractLLMProvider

logger = logging.getLogger("solidguard.llm.provider.registry")


class ProviderRegistry:
    """Registry for LLM providers. Supports multiple named providers."""

    def __init__(self):
        self._providers: dict[str, AbstractLLMProvider] = {}
        self._default_name: str | None = None

    def register(self, name: str, provider: AbstractLLMProvider, default: bool = False):
        self._providers[name] = provider
        if default or self._default_name is None:
            self._default_name = name

    def get(self, name: str | None = None) -> AbstractLLMProvider:
        if name and name in self._providers:
            return self._providers[name]
        if self._default_name and self._default_name in self._providers:
            return self._providers[self._default_name]
        raise ValueError(f"No provider found. Available: {list(self._providers.keys())}")

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def health_summary(self) -> dict:
        return {name: p.health_check() for name, p in self._providers.items()}

    def register_from_config(self, config) -> None:
        """根据 SolidGuardConfig 遍历 providers 并注册所有 Provider。

        Args:
            config: SolidGuardConfig 实例，包含 providers 字典
        """
        from .anthropic_provider import AnthropicProvider
        from .openai_provider import OpenAIProvider

        _api_mapping: dict[str, type[AbstractLLMProvider]] = {
            "openai": OpenAIProvider,
            "anthropic-messages": AnthropicProvider,
        }

        for name, provider_config in config.providers.items():
            api_type = provider_config.api
            provider_cls = _api_mapping.get(api_type)
            if provider_cls is None:
                logger.warning("跳过未知 api 类型的 Provider: name=%s, api=%s", name, api_type)
                continue
            provider = provider_cls(provider_config)
            is_default = name == "default"
            self.register(name, provider, default=is_default)
            logger.info("已注册 Provider: name=%s, api=%s, default=%s", name, api_type, is_default)


# --- 延迟初始化单例 ---

_provider_registry_instance: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """获取全局 ProviderRegistry 单例。

    首次调用时从配置加载并注册所有 Provider，后续直接返回缓存实例。
    """
    global _provider_registry_instance
    if _provider_registry_instance is None:
        from ..config import get_config

        _provider_registry_instance = ProviderRegistry()
        config = get_config()
        _provider_registry_instance.register_from_config(config)
    return _provider_registry_instance


def reset_provider_registry() -> None:
    """重置全局 ProviderRegistry 单例（用于测试）。"""
    global _provider_registry_instance
    _provider_registry_instance = None
