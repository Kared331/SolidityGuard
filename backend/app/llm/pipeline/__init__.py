"""LLM 审计 Pipeline 模块（下一代架构，演进中）。

架构演进规划：
    当前生产路径使用 `app.services.engine.llm_audit.LLMAuditEngine`（同步 Celery 任务）。
    本模块是下一代异步 pipeline 架构，设计目标：
      - 支持 SSE 流式进度推送（通过 progress_callback）
      - 基于 Pydantic schema 的结构化 prompt 渲染
      - 更清晰的 Provider / RAG / Security 分层

    迁移状态：未完成，尚未接入 tasks/run_llm_audit.py 调用链。
    迁移完成后将废弃 services/engine/llm_audit.py。

    保留此模块作为技术冗余，用于：
      1. 渐进式迁移，降低一次性重构风险
      2. SSE 流式审计功能的开发基础
      3. 面试时展示架构演进思路的参考
"""

from .audit_pipeline import AuditPipeline

__all__ = ["AuditPipeline"]
