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

logger = logging.getLogger("solidguard.services.embedding")
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


# 批量大小上限，避免单次请求过大
_BATCH_LIMIT = 32


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
def get_embedding_batch(texts: list[str]) -> list[list[float]]:
    """批量获取 embedding，单次 API 请求处理多条文本。

    相比循环调用 get_embedding，减少 N-1 次网络往返。
    对于 50 个函数，从 50×0.5s=25s 降至 1×1s≈1s。

    Args:
        texts: 待 embed 的文本列表

    Returns:
        与 texts 等长的 embedding 列表，顺序一致

    Raises:
        ValueError: 空列表或不支持的 Provider
        httpx.HTTPError: API 调用失败（重试后）
    """
    if not texts:
        return []

    name, provider = _resolve_embedding_provider()

    if provider.api == "local":
        return _get_local_embedding_batch(texts)

    if provider.api in ("openai", "openai-compatible"):
        api_key = provider.apiKey
        base_url = provider.baseUrl.rstrip("/")
        model = provider.models[0].id if provider.models else "text-embedding-3-small"

        all_embeddings: list[list[float]] = []
        # 分片处理，避免超出 API 单次输入上限
        for start in range(0, len(texts), _BATCH_LIMIT):
            chunk = texts[start:start + _BATCH_LIMIT]
            logger.debug(
                "请求批量 Embedding API: provider=%s, model=%s, batch_size=%d",
                name, model, len(chunk),
            )
            with _embedding_semaphore:
                resp = _embedding_client.post(
                    f"{base_url}/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": model, "input": chunk},
                )
                resp.raise_for_status()

                data = resp.json()
                if "data" not in data or len(data["data"]) != len(chunk):
                    raise ValueError(
                        f"批量 Embedding 响应数量不匹配: 期望 {len(chunk)}, 收到 {len(data.get('data', []))}"
                    )

                # OpenAI API 返回的 data 按 index 排序，确保顺序一致
                sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
                for item in sorted_data:
                    emb = item.get("embedding")
                    if not emb or not isinstance(emb, list):
                        raise ValueError("Invalid embedding format in batch response")
                    all_embeddings.append(emb)

        logger.info("批量 Embedding 完成: %d 条文本, 维度 %d", len(texts), len(all_embeddings[0]) if all_embeddings else 0)
        return all_embeddings

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


def _get_local_embedding_batch(texts: list[str]) -> list[list[float]]:
    """本地模型批量 embedding，单次 encode 调用处理多条文本。"""
    global _local_model
    if _local_model is None:
        with _model_lock:
            if _local_model is None:
                from sentence_transformers import SentenceTransformer

                model_path = os.path.join(_LOCAL_MODEL_DIR, "models--sentence-transformers--all-MiniLM-L6-v2", "snapshots")
                if os.path.isdir(model_path):
                    snapshots = os.listdir(model_path)
                    if snapshots:
                        actual_path = os.path.join(model_path, snapshots[0])
                        _local_model = SentenceTransformer(actual_path)
                        logger.info("Loaded local SentenceTransformer model from %s", actual_path)
                    else:
                        raise FileNotFoundError(f"No snapshots found in {model_path}")
                else:
                    _local_model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=_LOCAL_MODEL_DIR)
                    logger.info("Loaded SentenceTransformer model from cache_folder=%s", _LOCAL_MODEL_DIR)

    # SentenceTransformer.encode 原生支持批量输入
    embeddings = _local_model.encode(texts)
    return [emb.tolist() for emb in embeddings]
