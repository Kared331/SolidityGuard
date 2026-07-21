"""
LLM Module — independent module for LLM-powered smart contract auditing.
Provides:
- Provider abstraction (OpenAI, local) with observability
- YAML-based prompt management with versioning
- RAG pipeline (embedding + ChromaDB retrieval)
- Audit pipeline with streaming SSE support
- Security (input sanitization, output validation)
- Token budget management
"""
