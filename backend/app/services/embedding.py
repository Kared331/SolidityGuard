"""Embedding service with module-level model singleton (3.7).

The SentenceTransformer model is loaded once when the module is first
imported, so repeated calls do NOT re-download/re-load the model.
"""

import os

import httpx

from app.config import logger


def get_embedding(text: str) -> list[float]:
    provider = os.environ.get("EMBEDDING_PROVIDER", "openai")

    if provider == "openai":
        api_key = os.environ["EMBEDDING_API_KEY"]
        base_url = os.environ.get("EMBEDDING_BASE_URL", "https://api.openai.com/v1")

        resp = httpx.post(
            f"{base_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "text-embedding-3-small", "input": text},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    if provider == "local":
        return _get_local_embedding(text)

    raise ValueError(f"Unknown embedding provider: {provider}")


# ─── Module-level singleton for local model (3.7) ───────────────
_local_model = None


def _get_local_embedding(text: str) -> list[float]:
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer

        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded local SentenceTransformer model (all-MiniLM-L6-v2)")
    embedding = _local_model.encode(text)
    return embedding.tolist()
