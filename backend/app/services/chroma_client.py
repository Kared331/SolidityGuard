"""ChromaDB client with module-level singleton (3.18).

Thread-safe: uses a lock to prevent race conditions during initialization
in multi-threaded contexts (e.g., concurrent Celery tasks).
"""

from __future__ import annotations

import threading

import chromadb
from chromadb import Collection

from app.config import logger, settings

_persist_dir = settings.CHROMA_PERSIST_DIR
_client: chromadb.Client | None = None
_lock = threading.Lock()


def get_chroma_client() -> chromadb.Client:
    """Return the singleton PersistentClient (thread-safe)."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = chromadb.PersistentClient(path=_persist_dir)
                logger.info("ChromaDB client created (persist_dir=%s)", _persist_dir)
    return _client


def get_vulnerability_collection() -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(name="vulnerability_patterns")


def query_vulnerabilities(collection: Collection, embedding: list[float], top_k: int = 5) -> dict:
    """Query ChromaDB with tenacity retry and fallback (Sprint 3, blueprint 5.3).

    Returns {'documents': [[]], 'metadatas': [[]]} on failure.
    """
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((chromadb.errors.ChromaError, Exception)),
    )
    def _query_with_retry():
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )
        if not results.get("documents"):
            logger.warning("Empty ChromaDB results, returning fallback")
            return {"documents": [[]], "metadatas": [[]]}
        return results

    try:
        return _query_with_retry()
    except Exception:
        logger.error("ChromaDB query failed after retries, returning fallback")
        return {"documents": [[]], "metadatas": [[]]}


def query_vulnerabilities_batch(collection: Collection, embeddings: list[list[float]], top_k: int = 5) -> list[dict]:
    """批量查询 ChromaDB，单次 query 调用处理多个 embedding。

    相比循环调用 query_vulnerabilities，减少 N-1 次 ChromaDB 往返。
    ChromaDB query 原生支持传入多个 query_embeddings。

    Args:
        collection: ChromaDB collection
        embeddings: 多个查询向量
        top_k: 每个查询返回的近邻数

    Returns:
        与 embeddings 等长的结果列表，每个元素格式同 query_vulnerabilities
    """
    if not embeddings:
        return []

    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((chromadb.errors.ChromaError, Exception)),
    )
    def _batch_query_with_retry():
        results = collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
        )
        return results

    try:
        raw_results = _batch_query_with_retry()
    except Exception:
        logger.error("ChromaDB 批量查询失败（重试后），返回空结果集")
        return [{"documents": [[]], "metadatas": [[]]}] * len(embeddings)

    # ChromaDB 批量查询返回的 documents/metadatas 是二维列表，外层与输入 embeddings 等长
    documents_list = raw_results.get("documents", [])
    metadatas_list = raw_results.get("metadatas", [])

    results: list[dict] = []
    for i in range(len(embeddings)):
        docs = documents_list[i] if i < len(documents_list) else []
        metas = metadatas_list[i] if i < len(metadatas_list) else []
        if not docs:
            results.append({"documents": [[]], "metadatas": [[]]})
        else:
            results.append({"documents": [docs], "metadatas": [metas]})

    logger.debug("批量 RAG 检索完成: %d 条查询", len(embeddings))
    return results
