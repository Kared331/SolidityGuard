"""P0-2 / P0-3 / P0-4: LLM 调用健壮性单测（V5 mock 双轨——无真实 key 时的覆盖）。

覆盖：
- P0-2 Provider 重试：429 重试后成功（3 次调用）/ 401 立即失败零重试
  （openai 与 anthropic 双 Provider）
- P0-2 异常判别：is_retryable_llm_error / describe_llm_error 分类正确性
- P0-3 独立限流：并发 10 线程同时进入 LLM 段 ≤ maxConcurrentCalls；
  配置热改 maxConcurrentCalls=2 后不重启即生效（mtime 热加载）
- P0-4 事件循环复用：连续调用复用同一常驻循环（无 Event loop is closed）；
  多线程并发提交无循环相关异常

注意：conftest 会向 sys.modules 注入 app.llm.sync_wrapper 的 mock，
本文件在导入期临时取出真实模块后立即恢复 mock，避免影响其他测试。
"""
import asyncio
import importlib
import json
import os
import sys
import threading
import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

# Ensure backend package is importable
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# ── 取出真实 sync_wrapper（conftest 注入了 mock）────────────────
_conftest_sync_wrapper_mock = sys.modules.get("app.llm.sync_wrapper")
if "app.llm.sync_wrapper" in sys.modules:
    del sys.modules["app.llm.sync_wrapper"]

sync_wrapper = importlib.import_module("app.llm.sync_wrapper")

# 恢复 mock，其他测试模块导入 app.llm.sync_wrapper 仍拿到 conftest mock
if _conftest_sync_wrapper_mock is not None:
    sys.modules["app.llm.sync_wrapper"] = _conftest_sync_wrapper_mock

from app.llm.config import ModelConfig, ProviderConfig
from app.llm.provider import provider_registry as _pr_module
from app.llm.provider.anthropic_provider import AnthropicProvider
from app.llm.provider.base import (
    LLMResponse,
    describe_llm_error,
    is_retryable_llm_error,
)
from app.llm.provider.openai_provider import OpenAIProvider
from app.llm.provider.provider_registry import ProviderRegistry


# ── 测试辅助 ────────────────────────────────────────────────────


def _make_openai_provider() -> OpenAIProvider:
    cfg = ProviderConfig(
        apiKey="sk-test",
        baseUrl="http://test.local/v1",
        api="openai",
        defaultModel="gpt-4o",
        models=[ModelConfig(id="gpt-4o")],
    )
    return OpenAIProvider(cfg)


def _make_anthropic_provider() -> AnthropicProvider:
    cfg = ProviderConfig(
        apiKey="sk-test",
        baseUrl="http://test.local/v1",
        api="anthropic-messages",
        defaultModel="claude-3",
        models=[ModelConfig(id="claude-3")],
    )
    return AnthropicProvider(cfg)


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://test.local/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


def _fail_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.side_effect = _status_error(status_code)
    return resp


_OPENAI_PAYLOAD = {
    "choices": [{"message": {"content": "[]"}}],
    "model": "gpt-4o",
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}

_ANTHROPIC_PAYLOAD = {
    "content": [{"type": "text", "text": "[]"}],
    "model": "claude-3",
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


class _FakeProvider:
    """记录并发观测数据的假 Provider（P0-3/P0-4 用）。"""

    def __init__(self, delay: float = 0.15):
        self.delay = delay
        self.lock = threading.Lock()
        self.calls = 0
        self.in_flight = 0
        self.max_in_flight = 0

    async def chat_completion(
        self, system_prompt, user_prompt, temperature=0.2, max_tokens=4096
    ) -> LLMResponse:
        with self.lock:
            self.calls += 1
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
            return LLMResponse(content="[]", model="fake", usage={"total_tokens": 1})
        finally:
            with self.lock:
                self.in_flight -= 1

    def get_model_name(self) -> str:
        return "fake"

    def health_check(self) -> bool:
        return True


def _inject_fake_provider(monkeypatch, provider: _FakeProvider) -> _FakeProvider:
    """将假 Provider 注入 registry 单例（sync_wrapper 调用时经 get_provider_registry 取用）。"""
    registry = ProviderRegistry()
    registry.register("fake", provider, default=True)
    monkeypatch.setattr(_pr_module, "_provider_registry_instance", registry)
    return provider


def _run_concurrent_threads(target, count: int = 10) -> None:
    threads = [threading.Thread(target=target) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
        assert not t.is_alive(), "线程未在超时内完成（可能死锁）"


# ── P0-2: 异常判别（同步纯函数） ────────────────────────────────


def test_is_retryable_llm_error_classification():
    """429/5xx/连接错误/读超时可重试；4xx 凭证类与其他异常不重试。"""
    assert is_retryable_llm_error(_status_error(429))
    assert is_retryable_llm_error(_status_error(500))
    assert is_retryable_llm_error(_status_error(502))
    assert is_retryable_llm_error(_status_error(503))
    assert is_retryable_llm_error(_status_error(504))
    assert is_retryable_llm_error(httpx.ConnectError("boom"))
    assert is_retryable_llm_error(httpx.ReadTimeout("slow"))

    assert not is_retryable_llm_error(_status_error(400))
    assert not is_retryable_llm_error(_status_error(401))
    assert not is_retryable_llm_error(_status_error(403))
    assert not is_retryable_llm_error(_status_error(404))
    assert not is_retryable_llm_error(_status_error(422))
    assert not is_retryable_llm_error(ValueError("bad data"))


def test_describe_llm_error_observability():
    """S4：异常类型可区分；空消息异常回退类型名（空 WARNING 行防线）。"""
    assert describe_llm_error(_status_error(401)) == "HTTPStatusError 401"
    assert describe_llm_error(_status_error(429)) == "HTTPStatusError 429"
    assert describe_llm_error(httpx.ReadTimeout("")) == "ReadTimeout"
    assert describe_llm_error(httpx.ConnectError("")) == "ConnectError"
    # str(e) 为空时不得产生空描述
    assert describe_llm_error(ValueError("")) == "ValueError"
    assert describe_llm_error(ValueError("boom")) == "boom"


# ── P0-2: OpenAI Provider 重试 ─────────────────────────────────


async def test_openai_retry_on_429_then_success(monkeypatch):
    """429 两次后 200 → 调用成功且实际发起 3 次请求（重试 2 次）。"""
    monkeypatch.setattr(time, "sleep", lambda s: None)  # 跳过退避等待
    provider = _make_openai_provider()
    mock_client = MagicMock()
    mock_client.post = AsyncMock(
        side_effect=[
            _fail_response(429),
            _fail_response(429),
            _ok_response(_OPENAI_PAYLOAD),
        ]
    )
    provider._client = mock_client

    response = await provider.chat_completion("system", "user")

    assert response.content == "[]"
    assert response.usage["total_tokens"] == 15
    assert mock_client.post.await_count == 3


async def test_openai_no_retry_on_401(monkeypatch):
    """401（凭证类错误）→ 立即失败零重试。"""
    monkeypatch.setattr(time, "sleep", lambda s: None)
    provider = _make_openai_provider()
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=lambda *a, **kw: _fail_response(401))
    provider._client = mock_client

    with pytest.raises(httpx.HTTPStatusError):
        await provider.chat_completion("system", "user")

    assert mock_client.post.await_count == 1


# ── P0-2: Anthropic Provider 重试 ──────────────────────────────


def _patch_anthropic_client(monkeypatch, responses) -> AsyncMock:
    """替换 httpx.AsyncClient（anthropic 每次调用 async with 新建客户端）。"""
    post = AsyncMock(side_effect=list(responses))

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return await post(*args, **kwargs)

    import app.llm.provider.anthropic_provider as _anthropic_mod

    monkeypatch.setattr(_anthropic_mod.httpx, "AsyncClient", _FakeAsyncClient)
    return post


async def test_anthropic_retry_on_429_then_success(monkeypatch):
    """429 两次后 200 → 调用成功且实际发起 3 次请求。"""
    monkeypatch.setattr(time, "sleep", lambda s: None)
    provider = _make_anthropic_provider()
    post = _patch_anthropic_client(
        monkeypatch,
        [_fail_response(429), _fail_response(429), _ok_response(_ANTHROPIC_PAYLOAD)],
    )

    response = await provider.chat_completion("system", "user")

    assert response.content == "[]"
    assert response.usage["total_tokens"] == 15
    assert post.await_count == 3


async def test_anthropic_no_retry_on_401(monkeypatch):
    """401 → 立即失败零重试。"""
    monkeypatch.setattr(time, "sleep", lambda s: None)
    provider = _make_anthropic_provider()
    # 注意：side_effect 为列表时，元素会被直接作为返回值（lambda 不会被调用），
    # 因此这里必须放入构造好的 response mock，而非生成它的 lambda。
    post = _patch_anthropic_client(monkeypatch, [_fail_response(401)])

    with pytest.raises(httpx.HTTPStatusError):
        await provider.chat_completion("system", "user")

    assert post.await_count == 1


# ── P0-4: sync_wrapper 事件循环复用 ─────────────────────────────


def test_sync_wrapper_basic_call(monkeypatch):
    """基本调用返回 (content, usage) 元组。"""
    provider = _inject_fake_provider(monkeypatch, _FakeProvider(delay=0.01))

    content, usage = sync_wrapper.chat_completion([
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ])

    assert content == "[]"
    assert usage == {"total_tokens": 1}
    assert provider.calls == 1


def test_event_loop_reused_across_calls(monkeypatch):
    """P0-4：连续两次调用复用同一常驻事件循环，无 Event loop is closed。"""
    _inject_fake_provider(monkeypatch, _FakeProvider(delay=0.01))

    sync_wrapper.chat_completion([{"role": "user", "content": "a"}])
    loop_first = sync_wrapper._loop
    assert loop_first is not None
    assert not loop_first.is_closed()

    sync_wrapper.chat_completion([{"role": "user", "content": "b"}])

    assert sync_wrapper._loop is loop_first, "事件循环未被复用（每次新建）"
    assert not loop_first.is_closed()


def test_concurrent_calls_no_event_loop_errors(monkeypatch):
    """P0-4：多线程并发提交（模拟 ThreadPoolExecutor 文件级并行）无循环相关异常。"""
    _inject_fake_provider(monkeypatch, _FakeProvider(delay=0.05))
    errors: list[Exception] = []

    def _worker():
        try:
            sync_wrapper.chat_completion([{"role": "user", "content": "x"}])
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    _run_concurrent_threads(_worker, count=10)

    assert errors == [], f"并发调用出现异常: {errors}"


# ── P0-3: LLM 独立限流 ─────────────────────────────────────────


def test_semaphore_limits_concurrency(monkeypatch):
    """并发 10 线程调用，同时进入 LLM 段不超过配置值（默认 5）。"""
    provider = _inject_fake_provider(monkeypatch, _FakeProvider(delay=0.15))

    _run_concurrent_threads(
        lambda: sync_wrapper.chat_completion([{"role": "user", "content": "x"}]),
        count=10,
    )

    assert provider.calls == 10
    assert provider.max_in_flight <= 5, f"并发超限: {provider.max_in_flight} > 5"
    assert provider.max_in_flight >= 2, "未观测到真实并发（疑似串行）"


def test_semaphore_hot_reload(monkeypatch):
    """配置热改 maxConcurrentCalls=2 后不重启即生效（mtime 热加载）。"""
    config_path = os.environ["SOLIDGUARD_CONFIG"]
    with open(config_path, "r", encoding="utf-8") as f:
        original = json.load(f)

    modified = json.loads(json.dumps(original))
    modified["app"]["maxConcurrentCalls"] = 2
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(modified, f)
        # 显式 bump mtime，确保越过文件系统时间戳精度触发重载
        future = time.time() + 2
        os.utime(config_path, (future, future))

        provider = _inject_fake_provider(monkeypatch, _FakeProvider(delay=0.15))
        _run_concurrent_threads(
            lambda: sync_wrapper.chat_completion([{"role": "user", "content": "x"}]),
            count=10,
        )

        assert provider.calls == 10
        assert provider.max_in_flight <= 2, (
            f"热改后并发超限: {provider.max_in_flight} > 2"
        )
    finally:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(original, f)
