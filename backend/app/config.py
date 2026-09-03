import logging
import os
import sys
from functools import lru_cache

from pydantic import BaseModel  # noqa: F401

from app.llm.config import get_config

# logging 延迟初始化 — 在 Settings.__init__ 中通过配置设置等级
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("solidguard")


def _build_database_url() -> str:
    """从 POSTGRES_* 环境变量构建 DATABASE_URL。

    优先级：DATABASE_URL 环境变量 > POSTGRES_* 组件构建 > 默认值。
    docker-compose 通过 POSTGRES_HOST=postgres 覆盖 localhost，
    无需在 .env 里写死完整连接串。
    """
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit
    user = os.environ.get("POSTGRES_USER", "solidguard")
    password = os.environ.get("POSTGRES_PASSWORD", "changeme")
    db = os.environ.get("POSTGRES_DB", "solidguard")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def _build_redis_url() -> str:
    """从 REDIS_* 环境变量构建 REDIS_URL。

    优先级：REDIS_URL 环境变量 > REDIS_* 组件构建 > 默认值。
    """
    explicit = os.environ.get("REDIS_URL")
    if explicit:
        return explicit
    password = os.environ.get("REDIS_PASSWORD", "")
    host = os.environ.get("REDIS_HOST", "localhost")
    port = os.environ.get("REDIS_PORT", "6379")
    auth = f":{password}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


class Settings:
    def __init__(self):
        config = get_config()

        # app
        self.API_KEY: str = config.app.apiKey
        self.APP_PORT: int = config.app.port
        self.MAX_UPLOAD_SIZE_MB: int = config.app.maxUploadSizeMb
        self.CLEANUP_DAYS: int = config.app.cleanupDays
        self.LOG_LEVEL: str = config.app.logLevel
        self.CORS_ORIGINS: str = config.app.corsOrigins
        self.RATE_LIMIT: str = config.app.rateLimit
        self.UPLOAD_DIR: str = config.app.uploadDir
        self.REPORT_DIR: str = config.app.reportDir
        self.TOKEN_BUDGET_PER_PROJECT: int = config.app.tokenBudget
        self.MAX_LLM_CALLS_PER_PROJECT: int = config.app.maxLLMCallsPerProject
        self.MAX_CONCURRENT_LLM_CALLS: int = config.app.maxConcurrentCalls

        # database — 从 POSTGRES_* 组件构建，json 中的 url 留空即可
        self.DATABASE_URL: str = config.database.url or _build_database_url()
        self.DB_POOL_SIZE: int = config.database.poolSize
        self.DB_MAX_OVERFLOW: int = config.database.maxOverflow
        self.DB_POOL_RECYCLE: int = config.database.poolRecycle

        # redis — 从 REDIS_* 组件构建，json 中的 url 留空即可
        self.REDIS_URL: str = config.redis.url or _build_redis_url()

        # rag
        self.CHROMA_PERSIST_DIR: str = config.rag.chromaPersistDir
        self.RAG_TOP_K: int = config.rag.topK

        # 应用配置级别的 logging 等级
        logging.getLogger().setLevel(getattr(logging, self.LOG_LEVEL.upper(), logging.INFO))

        # P1-6: 启动边界校验——空 key 一次性 WARNING（不做请求级重复校验）
        if not self.API_KEY or self.API_KEY == "changeme":
            logging.warning(
                "⚠ API_KEY 未配置或仍为默认值（changeme）——"
                "全部业务请求将以 403 fail-closed 拒绝。"
                "请在 .env 中设置真实 API_KEY。"
            )
        if not self.LLM_API_KEY or self.LLM_API_KEY == "your-llm-api-key":
            logging.warning(
                "⚠ LLM_API_KEY 未配置——LLM 审计将走降级落库"
                "（空 key 不崩但无真实审计结果）。"
                "请在 .env 中设置真实 LLM_API_KEY。"
            )

    @property
    def LLM_API_KEY(self) -> str:
        """从环境变量读取 LLM_API_KEY（不在 solidguard.json 中明文存储）。"""
        return os.environ.get("LLM_API_KEY", "")

    @property
    def MAX_UPLOAD_SIZE(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
