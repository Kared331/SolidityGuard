"""Embedding service with module-level model singleton (3.7).

The SentenceTransformer model is loaded once when the module is first
imported, so repeated calls do NOT re-download/re-load the model.
Thread-safe: uses a lock to prevent race conditions during initialization.

6.x: Added tenacity retry, connection reuse via module-level httpx.Client.
7.x: Added rate limiting (Semaphore(5)), response validation.
8.x: Config via get_config(); removed os.environ for provider settings.
"""

import logging
import os
import threading

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.llm.config import get_config, ProviderConfig

logger = logging.getLogger("solidiguard.services.embedding")
_model_lock = threading.Lock()

# --- Rate limiter for embedding API calls (Sprint 2) -------------
_embedding_semaphore = threading.Semaphore(5)

# --- Module-level httpx.Client for connection reuse -------------
_embedding_client = httpx.Client(timeout=60)


def _resolve_embedding_provider() -> tuple[str, ProviderConfig]:
    """从配置文件解析 Embedding Provider。

    优先使用名为 "embedding" 的 Provider，不存在则回退到 default Provider。
    """
    config = get_config()
    if "embedding" in config.providers:
        logger.debug("使用配置中 'embedding' Provider")
        return "embedding", config.providers["embedding"]
    provider = config.get_default_provider()
    name = next(k for k, v in config.providers.items() if v is provider)
    logger.debug("使用 default Provider '%s' 作为 Embedding Provider", name)
    return name, provider


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(
        (
            httpx.HTTPStatusError,
            httpx.ConnectError,
            httpx.ReadTimeout,
        )
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def get_embedding(text: str) -> list[float]:
    name, provider = _resolve_embedding_provider()

    if provider.api == "local":
        return _get_local_embedding(text)

    if provider.api in ("openai", "openai-compatible"):
        api_key = provider.apiKey
        base_url = provider.baseUrl.rstrip("/")
        model = provider.models[0].id if provider.models else "text-embedding-3-small"

        logger.debug(
            "请求 Embedding API: provider=%s, base_url=%s, model=%s",
            name, base_url, model,
        )
        with _embedding_semaphore:
            resp = _embedding_client.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": text},
            )
            resp.raise_for_status()

            data = resp.json()
            if "data" not in data or len(data["data"]) == 0:
                raise ValueError("Empty embedding response from API")
            embedding = data["data"][0].get("embedding")
            if not embedding or not isinstance(embedding, list):
                raise ValueError("Invalid embedding format in response")

            logger.debug("Embedding 获取成功，维度: %d", len(embedding))
            return embedding

    raise ValueError(f"不支持的 Embedding Provider API 类型: {provider.api}")


# --- Module-level singleton for local model (3.7) ---------------
_local_model = None
_LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
_LOCAL_MODEL_DIR = os.path.normpath(_LOCAL_MODEL_DIR)


def _get_local_embedding(text: str) -> list[float]:
    global _local_model
    if _local_model is None:
        with _model_lock:
            if _local_model is None:
                from sentence_transformers import SentenceTransformer

                model_path = os.path.join(_LOCAL_MODEL_DIR, "models--sentence-transformers--all-MiniLM-L6-v2", "snapshots")
                if os.path.isdir(model_path):
                    # Find the snapshot hash directory
                    snapshots = os.listdir(model_path)
                    if snapshots:
                        actual_path = os.path.join(model_path, snapshots[0])
                        _local_model = SentenceTransformer(actual_path)
                        logger.info("Loaded local SentenceTransformer model from %s", actual_path)
                    else:
                        raise FileNotFoundError(f"No snapshots found in {model_path}")
                else:
                    # Fallback: load from HF cache folder
                    _local_model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=_LOCAL_MODEL_DIR)
                    logger.info("Loaded SentenceTransformer model from cache_folder=%s", _LOCAL_MODEL_DIR)
    embedding = _local_model.encode(text)
    return embedding.tolist()
