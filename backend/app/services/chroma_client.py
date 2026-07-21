"""ChromaDB client with module-level singleton (3.18).

Thread-safe: uses a lock to prevent race conditions during initialization
in multi-threaded contexts (e.g., concurrent Celery tasks).
"""

from __future__ import annotations

import os
import threading
from typing import Optional

import chromadb
from chromadb import Collection

from app.config import settings, logger

_persist_dir = settings.CHROMA_PERSIST_DIR
_client: Optional[chromadb.Client] = None
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


def query_vulnerabilities(
    collection: Collection, embedding: list[float], top_k: int = 5
) -> dict:
    """Query ChromaDB with tenacity retry and fallback (Sprint 3, blueprint 5.3).

    Returns {'documents': [[]], 'metadatas': [[]]} on failure.
    """
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
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
