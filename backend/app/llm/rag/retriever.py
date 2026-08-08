"""
ChromaDB retriever for vulnerability pattern lookups.

备选实现：本模块提供带 relevance 标签（HIGH/MEDIUM/LOW）的 format_rag_context，
比 services/chroma_client 的 query_vulnerabilities 更丰富。当前生产路径使用
chroma_client，本模块保留作为 RAG 上下文格式化的演进储备。

技术冗余：不删除，待后续 RAG 增强时迁移到此实现。
"""
from typing import Optional
import chromadb
from chromadb import Collection
from app.config import settings

# Default persist directory
CHROMA_DIR = settings.CHROMA_PERSIST_DIR
COLLECTION_NAME = "vulnerability_patterns"
TOP_K = settings.RAG_TOP_K


class VulnerabilityRetriever:
    def __init__(self, persist_dir: Optional[str] = None):
        self._persist_dir = persist_dir or CHROMA_DIR
        self._client: Optional[chromadb.PersistentClient] = None

    @property
    def client(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        return self._client

    def get_collection(self) -> Collection:
        return self.client.get_or_create_collection(name=COLLECTION_NAME)

    def query(self, embedding: list[float], top_k: int = TOP_K) -> dict:
        try:
            collection = self.get_collection()
            results = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            return results if results else {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        except Exception as e:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "error": str(e)}

    def format_rag_context(self, results: dict) -> str:
        """Format RAG query results into a prompt-friendly string."""
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return "No similar vulnerability patterns found in knowledge base."

        lines = ["## Similar Vulnerability Patterns (from SWC Knowledge Base):\n"]
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
            relevance = "HIGH" if dist < 0.3 else "MEDIUM" if dist < 0.6 else "LOW"
            title = meta.get("title", "Unknown") if meta else "Unknown"
            severity = meta.get("severity", "") if meta else ""
            lines.append(f"### Pattern {i}: {title} [{severity}] (Relevance: {relevance})")
            lines.append(doc[:800])
            lines.append("")
        return "\n".join(lines)

    def health_check(self) -> bool:
        try:
            self.get_collection()
            return True
        except Exception:
            return False


vulnerability_retriever = VulnerabilityRetriever()
