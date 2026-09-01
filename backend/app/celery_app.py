"""Celery application with beat schedule for cleanup (5.20).

P1-9: worker 优雅关闭超时匹配任务时长（S5）。
    原 worker_shutdown_timeout=30 小于 LLM 审计大项目时长，warm shutdown
    超时后强杀导致任务无声作废。现调整为可配置（solidguard.json
    app.workerShutdownTimeout，默认 300s），根治依赖 P1-1 幂等 + 任务级重试。

P1-4: worker_process_shutdown 信号 → 关闭 Provider 客户端 + 常驻事件循环。
    与 FastAPI 侧 shutdown 钩子对称，避免进程退出时 Unclosed client session 警告。
"""

import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_shutdown

from app.config import settings

logger = logging.getLogger("solidguard.celery")


def _get_worker_shutdown_timeout() -> int:
    """从 solidguard.json 读取 worker 优雅关闭超时（秒）。

    走 A3 单一事实来源 + mtime 热加载；缺省 300s。
    """
    try:
        from app.llm.config import get_config

        return get_config().app.workerShutdownTimeout
    except Exception:
        return 300


celery = Celery("solidguard", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_shutdown_timeout=_get_worker_shutdown_timeout(),
)

# 5.20: Periodic cleanup of old uploads and reports
celery.autodiscover_tasks(["app.tasks"])

celery.conf.beat_schedule = {
    "cleanup-old-files": {
        "task": "app.tasks.cleanup.cleanup_old_files",
        "schedule": crontab(hour=3, minute=0),  # Run daily at 3 AM UTC
    },
}


# ── P1-4: worker 进程退出时统一关闭 Provider 客户端 + 常驻事件循环 ──
@worker_process_shutdown.connect
def _close_llm_resources(**kwargs) -> None:
    """worker 进程退出钩子：关闭 Provider HTTP 客户端与常驻事件循环。

    与 FastAPI 侧 main.py 的 shutdown 钩子对称，避免进程退出时
    出现 Unclosed client session 警告（S7 生命周期统一）。
    """
    try:
        from app.llm.provider.provider_registry import get_provider_registry

        registry = get_provider_registry()
        provider = registry.get()
        if hasattr(provider, "close"):
            import asyncio

            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(provider.close())
                loop.close()
            except Exception:
                pass
        logger.info("worker 退出：Provider 客户端已关闭")
    except Exception as exc:
        logger.debug("worker 退出关闭 Provider 时跳过: %s", exc)

    # 关闭 sync_wrapper 常驻事件循环（若已初始化）
    try:
        from app.llm import sync_wrapper

        if sync_wrapper._loop is not None and not sync_wrapper._loop.is_closed():
            sync_wrapper._loop.call_soon_threadsafe(sync_wrapper._loop.stop)
            sync_wrapper._loop.close()
            logger.info("worker 退出：常驻事件循环已关闭")
    except Exception as exc:
        logger.debug("worker 退出关闭事件循环时跳过: %s", exc)
