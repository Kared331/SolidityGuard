"""同步包装器：桥接异步 LLM Provider 与同步调用方（如 Celery 任务）。

P0-3 LLM 调用独立限流：
    threading.Semaphore 限制同时进入 LLM 调用段的并发数，
    配置项 app.maxConcurrentCalls（solidguard.json，mtime 热加载），
    默认 5 与文件级 ThreadPoolExecutor(5) 对齐（约束 A5）。
    限流语义声明（E7）：进程内信号量，仅对单 worker 进程生效；
    当前单机单 worker 部署可接受，未来多 worker 需换 Redis 分布式信号量。

P0-4 事件循环复用修复（方案 B 变体）：
    原实现每次 asyncio.run() 新建并销毁事件循环，而 OpenAIProvider
    持有构造时创建的长生命周期 httpx.AsyncClient，跨循环复用其连接池
    存在 "Event loop is closed" 风险。
    现改为模块级常驻事件循环，运行于专用守护线程，调用方经
    run_coroutine_threadsafe 提交协程——既保留连接复用，又保证
    ThreadPoolExecutor 多线程并发调用安全（直接共享 run_until_complete
    会被多线程并发进入同一循环，非线程安全）。
    严格懒初始化：禁止 import 时创建循环（Celery prefork fork 安全），
    首次 LLM 调用时才创建，fork 后各 worker 进程各自持有。
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Tuple

from .config import get_config

logger = logging.getLogger("solidguard.llm.sync_wrapper")

# ── P0-3: LLM 独立限流信号量（懒初始化 + 配置热加载） ──────────
_llm_semaphore: threading.Semaphore | None = None
_llm_semaphore_limit: int = 0
_semaphore_lock = threading.Lock()


def _get_semaphore() -> threading.Semaphore:
    """获取 LLM 并发限流信号量。

    每次调用读取 get_config()（mtime 缓存热加载），配置变化时
    重建信号量，实现不重启即可调整 maxConcurrentCalls。
    """
    global _llm_semaphore, _llm_semaphore_limit
    limit = get_config().app.maxConcurrentCalls
    if _llm_semaphore is None or limit != _llm_semaphore_limit:
        with _semaphore_lock:
            if _llm_semaphore is None or limit != _llm_semaphore_limit:
                _llm_semaphore = threading.Semaphore(limit)
                _llm_semaphore_limit = limit
                logger.info("LLM 并发限流信号量已初始化: maxConcurrentCalls=%d", limit)
    return _llm_semaphore


# ── P0-4: 常驻事件循环（专用守护线程，懒初始化） ────────────────
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    """获取常驻事件循环（运行于专用守护线程）。

    守护线程随进程退出，无需显式 join；循环不主动关闭，
    provider 客户端的统一关闭在 P1-4 收口。
    """
    global _loop, _loop_thread
    if _loop is None or _loop.is_closed():
        with _loop_lock:
            if _loop is None or _loop.is_closed():
                _loop = asyncio.new_event_loop()
                _loop_thread = threading.Thread(
                    target=_loop.run_forever,
                    name="solidguard-llm-loop",
                    daemon=True,
                )
                _loop_thread.start()
                logger.info("LLM 常驻事件循环线程已启动（懒初始化）")
    return _loop


def chat_completion(
    messages: list[dict], temperature: float = 0.2
) -> Tuple[str, dict]:
    """同步版聊天补全接口。

    Args:
        messages: OpenAI 格式的消息列表
        temperature: 采样温度

    Returns:
        (response_content, usage_dict)
    """
    from .provider.provider_registry import get_provider_registry

    registry = get_provider_registry()
    provider = registry.get()

    system_prompt = ""
    user_parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            user_parts.append(content)

    user_prompt = "\n".join(user_parts) if user_parts else ""

    async def _call():
        response = await provider.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        return response.content, response.usage

    # 限流在调用线程获取（信号量持有期间含重试等待）；
    # 协程提交到常驻循环线程执行，future.result() 阻塞等待结果
    with _get_semaphore():
        future = asyncio.run_coroutine_threadsafe(_call(), _get_loop())
        return future.result()
