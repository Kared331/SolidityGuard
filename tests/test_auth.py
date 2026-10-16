"""Authentication tests (A2/A3).

Covers:
- verify_api_key 三态：缺 key / 错 key / 正确 key
- fail-closed：API_KEY 未配置时拒绝全部请求
- A3：认证失败审计日志、非 ASCII key 不触发 500
- 真实 app 认证门：无/错 key 必须在触达业务逻辑前 403
- /health 不受认证门保护

背景：此前认证边界无任何测试回归保护（test_api 恒带正确 key），
auth 依赖一旦被误删测试仍全绿。本文件补齐该缺口。
"""

import logging
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _mock_request(path: str = "/api/v1/projects") -> MagicMock:
    """构造 verify_api_key 直调用的最小 Request 替身。"""
    request = MagicMock()
    request.url.path = path
    request.client = None
    return request


# ─── verify_api_key 单元测试 ──────────────────────────────────────

class TestVerifyApiKeyUnit:
    """直接调用 verify_api_key（settings 来自 conftest 测试配置）。"""

    @pytest.mark.asyncio
    async def test_missing_key_rejected_403(self):
        from fastapi import HTTPException

        from app.auth import verify_api_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(_mock_request(), api_key=None)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_wrong_key_rejected_403(self):
        from fastapi import HTTPException

        from app.auth import verify_api_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(_mock_request(), api_key="wrong-key")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_correct_key_passes(self):
        from app.auth import verify_api_key
        from app.config import settings

        result = await verify_api_key(_mock_request(), api_key=settings.API_KEY)
        assert result is None

    @pytest.mark.asyncio
    async def test_fail_closed_when_api_key_not_configured(self, monkeypatch):
        """API_KEY 为空时必须 fail-closed（403），而非放行。"""
        from fastapi import HTTPException

        from app.auth import verify_api_key
        from app.config import settings

        monkeypatch.setattr(settings, "API_KEY", "")
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(_mock_request(), api_key=None)
        assert exc_info.value.status_code == 403
        assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_wrong_key_emits_audit_log(self, caplog):
        """A3: 认证失败必须产出审计 WARNING（不含 key 本身）。"""
        from fastapi import HTTPException

        from app.auth import verify_api_key

        with caplog.at_level(logging.WARNING, logger="solidguard"):
            with pytest.raises(HTTPException):
                await verify_api_key(_mock_request(), api_key="secret-attempt")

        assert any("认证失败" in r.getMessage() for r in caplog.records)
        assert not any("secret-attempt" in r.getMessage() for r in caplog.records)

    @pytest.mark.asyncio
    async def test_non_ascii_key_rejected_not_500(self):
        """A3: bytes 化比较——非 ASCII key 走 403 而非 compare_digest TypeError 500。"""
        from fastapi import HTTPException

        from app.auth import verify_api_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(_mock_request(), api_key="clé-café")
        assert exc_info.value.status_code == 403


# ─── 真实 app 认证门端到端 ────────────────────────────────────────

class TestAuthGateEndToEnd:
    """无/错 key 经真实 app 请求业务端点必须 403。

    认证失败在依赖解析阶段短路，不会触达 DB 依赖，无需 mock 数据库。
    """

    @pytest.fixture
    def anon_client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_missing_header_returns_403(self, anon_client):
        resp = anon_client.get("/api/v1/projects")
        assert resp.status_code == 403

    def test_wrong_key_returns_403(self, anon_client):
        resp = anon_client.get("/api/v1/projects", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 403

    def test_health_not_auth_gated(self, anon_client):
        """/health 无认证门，即使依赖不可达也返回非 403 状态（200/503）。"""
        resp = anon_client.get("/health")
        assert resp.status_code != 403
