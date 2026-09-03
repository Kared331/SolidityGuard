"""Redis Pub/Sub 实时推送管理器。

为审计流水线提供实时进度推送能力，替代数据库轮询机制。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from .audit_pipeline import AuditProgress

logger = logging.getLogger("solidguard.llm.stream")

# Redis channel 命名规范
_CHANNEL_PREFIX = "solidguard:project"


def _channel_name(project_id: int) -> str:
    return f"{_CHANNEL_PREFIX}:{project_id}:events"


class AuditStreamManager:
    """基于 Redis Pub/Sub 的审计进度流管理器。"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def close(self):
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def publish_progress(self, project_id: int, progress: AuditProgress):
        """发布审计进度事件到 Redis Pub/Sub。"""
        event = {
            "type": "audit_progress",
            "project_id": project_id,
            "phase": progress.phase,
            "current_file": progress.current_file,
            "current_function": progress.current_function,
            "total_functions": progress.total_functions,
            "completed_functions": progress.completed_functions,
            "findings_so_far": progress.findings_so_far,
        }
        await self._publish(project_id, event)

    async def publish_finding(self, project_id: int, finding: dict):
        """发布单个审计发现到 Redis Pub/Sub。"""
        event = {
            "type": "audit_finding",
            "project_id": project_id,
            "finding": finding,
        }
        await self._publish(project_id, event)

    async def publish_status_change(self, project_id: int, new_status: str):
        """发布项目状态变更事件。"""
        event = {
            "type": "status_change",
            "project_id": project_id,
            "status": new_status,
        }
        await self._publish(project_id, event)

    async def publish_task_event(self, project_id: int, event_type: str, count: int):
        """发布任务完成事件（如 new_detections, new_fuzz_results 等）。"""
        event = {
            "type": event_type,
            "project_id": project_id,
            "count": count,
        }
        await self._publish(project_id, event)

    async def _publish(self, project_id: int, event: dict):
        """发布事件到指定项目的 Redis channel。"""
        try:
            redis = await self._get_redis()
            channel = _channel_name(project_id)
            payload = json.dumps(event, default=str)
            await redis.publish(channel, payload)
            logger.debug("Published to %s: %s", channel, event.get("type"))
        except Exception as e:
            logger.error("Redis publish failed for project %d: %s", project_id, e)

    async def health_check(self) -> bool:
        """检查 Redis 连接是否可用。"""
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception:
            return False

    async def subscribe(self, project_id: int) -> AsyncIterator[dict]:
        """订阅指定项目的实时事件流。

        使用 Redis Pub/Sub 替代数据库轮询，实现毫秒级推送。
        """
        pubsub = None
        try:
            redis = await self._get_redis()
            pubsub = redis.pubsub()
            channel = _channel_name(project_id)
            await pubsub.subscribe(channel)
            logger.info("Subscribed to Redis channel: %s", channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning("Failed to parse Redis message: %s", e)
        except asyncio.CancelledError:
            logger.info("Subscription cancelled for project %d", project_id)
        except Exception as e:
            logger.error("Redis subscription error for project %d: %s", project_id, e)
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe()
                    await pubsub.aclose()
                except Exception:
                    pass


# 全局单例
audit_stream: AuditStreamManager | None = None


def get_audit_stream() -> AuditStreamManager:
    """获取全局 AuditStreamManager 单例。"""
    global audit_stream
    if audit_stream is None:
        from app.config import settings

        audit_stream = AuditStreamManager(redis_url=settings.REDIS_URL)
    return audit_stream
