"""Task 调度抽象层 — 解耦 Service 层与 Task 层。

设计目标：
- Service 层依赖 TaskDispatcher 接口，不直接 import app.tasks.*
- 打破 Service ↔ Task 双向依赖，两层可独立测试
- 测试时注入 mock dispatcher，无需 Celery 运行时

P1-1 任务幂等：
    派发前查询 Celery 是否有同项目同类型的非终态任务，存在则拒绝。
    幂等只拦截「并行重复触发」，终态（succeeded/failed）后放行——
    用户主动重跑不算重复。无 schema 变更（方案 A）。

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

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("solidguard.services.task_dispatcher")


class TaskAlreadyRunning(Exception):
    """同项目同类型的任务已在运行中（幂等拦截）。"""

    def __init__(self, project_id: int, task_type: str):
        self.project_id = project_id
        self.task_type = task_type
        super().__init__(
            f"项目 {project_id} 已有 {task_type} 任务在运行中，"
            f"请等待当前任务完成后再触发"
        )


@runtime_checkable
class TaskDispatcher(Protocol):
    """Task 调度接口，Service 层通过此接口触发异步任务。"""

    def dispatch_analysis(self, project_id: int) -> str:
        """触发项目分析任务，返回 task_id。"""
        ...

    def dispatch_fuzz(self, project_id: int) -> str:
        """触发 Fuzz 测试任务，返回 task_id。"""
        ...

    def dispatch_llm_audit(self, project_id: int) -> str:
        """触发 LLM 审计任务，返回 task_id。"""
        ...

    def dispatch_report(self, project_id: int, output_format: str) -> str:
        """触发报告生成任务，返回 task_id。"""
        ...


# P1-1: 任务类型 → Celery task name 映射（用于 inspect 活跃任务匹配）
_TASK_TYPE_TO_NAME = {
    "analysis": "run_slither",
    "llm_audit": "run_llm_audit",
    "fuzz": "run_fuzzer",
    "report": "generate_report",
}


def _has_active_task(project_id: int, task_type: str) -> bool:
    """查询 Celery 是否有同项目同类型的活跃任务（运行中或排队中）。

    用 celery.control.inspect().active() 查询当前 worker 正在执行的任务，
    匹配 args[0] == project_id 且 task name 匹配。
    本地单 worker 场景足够拦截快速重复触发。
    """
    try:
        from app.celery_app import celery

        inspect = celery.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        target_name = _TASK_TYPE_TO_NAME.get(task_type, task_type)

        for _worker, tasks in active.items():
            for task in tasks:
                name = task.get("name", "")
                # task name 可能带 app.tasks. 前缀
                if not name.endswith(target_name):
                    continue
                args = task.get("args", [])
                # pipeline 任务 args[0] 为 project_id
                if args and str(args[0]) == str(project_id):
                    return True
        return False
    except Exception as exc:
        # broker 不可达时放行（不阻塞正常派发）
        logger.debug("幂等检查失败，放行: %s", exc)
        return False


class CeleryTaskDispatcher:
    """Celery 实现 — 延迟 import tasks 模块，避免循环依赖。

    所有 import 放在方法内部，确保 Service 层 import 本模块时
    不会触发 tasks 模块加载。

    P1-1: 派发前检查同项目同类型是否有活跃任务，有则抛 TaskAlreadyRunning。
    """

    def dispatch_analysis(self, project_id: int) -> str:
        if _has_active_task(project_id, "analysis"):
            raise TaskAlreadyRunning(project_id, "analyze")
        from app.tasks.pipeline import build_analysis_pipeline
        result = build_analysis_pipeline(project_id).apply_async()
        return result.id

    def dispatch_fuzz(self, project_id: int) -> str:
        if _has_active_task(project_id, "fuzz"):
            raise TaskAlreadyRunning(project_id, "fuzz")
        from app.tasks.pipeline import build_fuzz_pipeline
        result = build_fuzz_pipeline(project_id).apply_async()
        return result.id

    def dispatch_llm_audit(self, project_id: int) -> str:
        if _has_active_task(project_id, "llm_audit"):
            raise TaskAlreadyRunning(project_id, "llm-audit")
        from app.tasks.pipeline import build_llm_audit_pipeline
        result = build_llm_audit_pipeline(project_id).apply_async()
        return result.id

    def dispatch_report(self, project_id: int, output_format: str) -> str:
        if _has_active_task(project_id, "report"):
            raise TaskAlreadyRunning(project_id, "report")
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
