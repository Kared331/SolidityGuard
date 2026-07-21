import sys
import logging
from functools import lru_cache

from pydantic import BaseModel  # noqa: F401

from app.llm.config import get_config

# logging 延迟初始化 — 在 Settings.__init__ 中通过配置设置等级
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("solidiguard")


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

        # database
        self.DATABASE_URL: str = config.database.url
        self.DB_POOL_SIZE: int = config.database.poolSize
        self.DB_MAX_OVERFLOW: int = config.database.maxOverflow
        self.DB_POOL_RECYCLE: int = config.database.poolRecycle

        # redis
        self.REDIS_URL: str = config.redis.url

        # rag
        self.CHROMA_PERSIST_DIR: str = config.rag.chromaPersistDir
        self.RAG_TOP_K: int = config.rag.topK

        # 应用配置级别的 logging 等级
        logging.getLogger().setLevel(
            getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
        )

    @property
    def MAX_UPLOAD_SIZE(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
