"""Task 调度抽象层 — 解耦 Service 层与 Task 层。

设计目标：
- Service 层依赖 TaskDispatcher 接口，不直接 import app.tasks.*
- 打破 Service ↔ Task 双向依赖，两层可独立测试
- 测试时注入 mock dispatcher，无需 Celery 运行时

用法：
    # 生产环境（默认自动使用 CeleryTaskDispatcher）
    from app.services.task_dispatcher import get_task_dispatcher
    dispatcher = get_task_dispatcher()
    task_id = dispatcher.dispatch_analysis(project_id)

    # 测试环境
    from app.services.task_dispatcher import set_task_dispatcher
    set_task_dispatcher(MockDispatcher())
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TaskDispatcher(Protocol):
    """Task 调度接口，Service 层通过此接口触发异步任务。"""

    def dispatch_analysis(self, project_id: int) -> str:
        """触发项目分析任务，返回 task_id。"""
        ...

    def dispatch_llm_audit(self, project_id: int) -> str:
        """触发 LLM 审计任务，返回 task_id。"""
        ...

    def dispatch_report(self, project_id: int, output_format: str) -> str:
        """触发报告生成任务，返回 task_id。"""
        ...


class CeleryTaskDispatcher:
    """Celery 实现 — 延迟 import tasks 模块，避免循环依赖。

    所有 import 放在方法内部，确保 Service 层 import 本模块时
    不会触发 tasks 模块加载。
    """

    def dispatch_analysis(self, project_id: int) -> str:
        from app.tasks.pipeline import build_analysis_pipeline
        result = build_analysis_pipeline(project_id).apply_async()
        return result.id

    def dispatch_llm_audit(self, project_id: int) -> str:
        from app.tasks.pipeline import build_llm_audit_pipeline
        result = build_llm_audit_pipeline(project_id).apply_async()
        return result.id

    def dispatch_report(self, project_id: int, output_format: str) -> str:
        from app.tasks.pipeline import build_report_pipeline
        result = build_report_pipeline(project_id, output_format).apply_async()
        return result.id


# 默认单例，生产环境使用 Celery 实现
_dispatcher: TaskDispatcher = CeleryTaskDispatcher()


def get_task_dispatcher() -> TaskDispatcher:
    """获取当前 TaskDispatcher 实例。"""
    return _dispatcher


def set_task_dispatcher(dispatcher: TaskDispatcher) -> None:
    """注入自定义 TaskDispatcher（测试用）。"""
    global _dispatcher
    _dispatcher = dispatcher


def reset_task_dispatcher() -> None:
    """重置为默认 Celery 实现（测试清理用）。"""
    global _dispatcher
    _dispatcher = CeleryTaskDispatcher()
