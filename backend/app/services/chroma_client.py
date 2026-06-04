"""ChromaDB client with module-level singleton (3.18)."""

import os

import chromadb
from chromadb import Collection

from app.config import logger

_persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_data")
_client: chromadb.Client | None = None


def get_chroma_client() -> chromadb.Client:
    """Return the singleton PersistentClient."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=_persist_dir)
        logger.info("ChromaDB client created (persist_dir=%s)", _persist_dir)
    return _client


def get_vulnerability_collection() -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(name="vulnerability_patterns")
