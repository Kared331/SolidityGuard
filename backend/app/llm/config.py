"""JSON 配置文件解析器。

从 solidguard.json 加载全部应用配置，支持 ${ENV_VAR} 语法引用环境变量。
配置文件路径通过 SOLIDGUARD_CONFIG 环境变量指定，默认 ./solidguard.json。
"""

from __future__ import annotations

import json
import os
import re
import logging
from functools import lru_cache
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("solidguard.config")

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置值中的 ${ENV_VAR} 引用。"""
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            env_val = os.environ.get(var_name)
            if env_val is None:
                raise ValueError(
                    f"环境变量 '{var_name}' 未设置，"
                    f"但配置文件中引用了 ${{{var_name}}}"
                )
            return env_val
        return _ENV_VAR_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


# --- Pydantic 配置模型 ---

class ModelConfig(BaseModel):
    """单个模型的配置。"""
    id: str
    name: str = ""
    maxTokens: int = 4096
    contextWindow: int = 128000
    reasoning: bool = False
    input: list[str] = Field(default_factory=lambda: ["text"])


class ProviderConfig(BaseModel):
    """单个 LLM Provider 的配置。"""
    apiKey: str = ""
    baseUrl: str = ""
    api: str = "openai"
    models: list[ModelConfig] = Field(default_factory=list)
    defaultModel: str = ""

    def get_model(self, model_id: Optional[str] = None) -> ModelConfig:
        """获取指定模型，未指定时返回第一个。"""
        if model_id:
            for m in self.models:
                if m.id == model_id:
                    return m
        if self.models:
            return self.models[0]
        raise ValueError(f"Provider 中没有配置任何模型")


class AppConfig(BaseModel):
    """应用基础配置。"""
    apiKey: str = ""
    port: int = 8000
    maxUploadSizeMb: int = 50
    cleanupDays: int = 30
    logLevel: str = "INFO"
    corsOrigins: str = "http://localhost:3000,http://localhost:5173"
    rateLimit: str = "60/minute"
    uploadDir: str = "uploads"
    reportDir: str = "reports"
    tokenBudget: int = 500000
    maxLLMCallsPerProject: int = 100


class DatabaseConfig(BaseModel):
    """数据库配置。"""
    url: str = ""
    poolSize: int = 10
    maxOverflow: int = 20
    poolRecycle: int = 3600


class RedisConfig(BaseModel):
    """Redis 配置。"""
    url: str = "redis://localhost:6379/0"


class RagConfig(BaseModel):
    """RAG 相关配置。"""
    chromaPersistDir: str = "./chroma_data"
    topK: int = 5


class SolidGuardConfig(BaseModel):
    """SolidGuard 完整配置。"""
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    rag: RagConfig = Field(default_factory=RagConfig)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    def get_default_provider(self) -> ProviderConfig:
        """获取名为 'default' 的 Provider，不存在时使用第一个。"""
        if "default" in self.providers:
            return self.providers["default"]
        if self.providers:
            return next(iter(self.providers.values()))
        raise ValueError("配置文件中没有定义任何 LLM Provider")

    def get_provider(self, name: Optional[str] = None) -> ProviderConfig:
        """按名称获取 Provider，未指定时返回 default。"""
        if name and name in self.providers:
            return self.providers[name]
        return self.get_default_provider()


def load_config(path: Optional[str] = None) -> SolidGuardConfig:
    """加载并校验 JSON 配置文件。

    Args:
        path: 配置文件路径，为 None 时从 SOLIDGUARD_CONFIG 环境变量读取，
              默认 ./solidguard.json

    Returns:
        SolidGuardConfig 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: JSON 格式错误或校验失败
    """
    if path is None:
        path = os.environ.get("SOLIDGUARD_CONFIG", "./solidguard.json")

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"配置文件不存在: {path}\n"
            f"请复制 solidguard.json.example 为 solidguard.json 并填写配置。\n"
            f"或设置 SOLIDGUARD_CONFIG 环境变量指向配置文件路径。"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件 JSON 格式错误: {path}\n{e}") from e

    try:
        resolved = _resolve_env_vars(raw)
    except ValueError as e:
        raise ValueError(f"配置文件环境变量解析失败: {e}") from e

    try:
        return SolidGuardConfig(**resolved)
    except Exception as e:
        raise ValueError(f"配置文件校验失败: {e}") from e


_config_instance: Optional[SolidGuardConfig] = None
_config_mtime: float = 0.0


def get_config(path: Optional[str] = None) -> SolidGuardConfig:
    """获取配置单例，支持基于文件 mtime 的热加载。

    文件修改后下次调用自动重新加载，改完 solidguard.json 保存即生效，
    无需重启服务。切换 provider / 改 model / 调 tokenBudget 都是即时的。
    """
    global _config_instance, _config_mtime

    if path is None:
        path = os.environ.get("SOLIDGUARD_CONFIG", "./solidguard.json")

    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        # 文件不存在时回退到缓存或抛错
        if _config_instance is not None:
            return _config_instance
        return load_config(path)

    if _config_instance is None or current_mtime != _config_mtime:
        _config_instance = load_config(path)
        _config_mtime = current_mtime
        logger.info("配置已加载: %s (mtime=%d)", path, int(current_mtime))

    return _config_instance


def reset_config() -> None:
    """重置配置单例（用于测试）。"""
    global _config_instance, _config_mtime
    _config_instance = None
    _config_mtime = 0.0
