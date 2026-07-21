"""Health check for RAG components: Embedding + ChromaDB."""
from .retriever import vulnerability_retriever


def check_rag_health() -> dict:
    return {
        "chromadb": "healthy" if vulnerability_retriever.health_check() else "unhealthy",
    }
