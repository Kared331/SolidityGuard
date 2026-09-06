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

    导入策略（PEP 562 延迟导出）：audit_pipeline 会连带加载 Provider/RAG
    /Prompts 等整条 LLM 链。而本包内的 stream 模块被 run_slither/run_fuzzer
    等非 LLM 任务引用（B2 SSE 事件发布），若 __init__ 顶层导入
    audit_pipeline，会迫使这些任务无辜背负 LLM 依赖。故改为 __getattr__
    惰性导出，仅显式访问 AuditPipeline 时才加载 audit_pipeline。
"""

__all__ = ["AuditPipeline"]


def __getattr__(name: str):
    if name == "AuditPipeline":
        from .audit_pipeline import AuditPipeline

        return AuditPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
