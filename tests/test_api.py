"""Integration tests for SolidGuard API endpoints using FastAPI TestClient.

Tests:
- POST /api/v1/projects — upload with valid .sol file
- GET /api/v1/projects/{id}/files — list files
- POST /api/v1/projects/{id}/analyze — trigger analysis
- GET /health — health endpoint
- POST /api/v1/detections/{id}/mark-false-positive — marking FP
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def app_client():
    """Return a TestClient with all external dependencies mocked."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import get_db
    from app.config import settings

    mock_session = AsyncMock()
    mock_session.get = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, headers={"X-API-Key": settings.API_KEY})
    yield client, mock_session
    app.dependency_overrides.clear()


# ─── Health Endpoint ──────────────────────────────────────────────

class TestHealthEndpoint:
    """Tests for GET /health."""

    @patch("app.main.async_session")
    @patch("app.main.aioredis")
    def test_health_returns_200_with_checks(self, mock_redis, mock_session):
        """Health endpoint should return 200 with a checks dict."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.dependencies import get_db

        mock_db = AsyncMock()
        async def override_get_db():
            yield mock_db
        app.dependency_overrides[get_db] = override_get_db

        mock_session_instance = AsyncMock()
        mock_session_instance.execute = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis_instance.aclose = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance

        client = TestClient(app)
        resp = client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)

        app.dependency_overrides.clear()


# ─── Project Upload ───────────────────────────────────────────────

class TestProjectUpload:
    """Tests for POST /api/v1/projects."""

    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_proj")
    @patch("os.makedirs")
    @patch("builtins.open", MagicMock())
    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_upload_valid_sol_file(
        self, mock_realpath, mock_makedirs, mock_get_dir, mock_process, app_client
    ):
        client, mock_db = app_client

        project = MagicMock()
        project.id = 1
        project.name = "Test"
        project.status = "uploaded"

        async def fake_refresh(p):
            p.id = 1
            p.name = "Test"
            p.status = "uploaded"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)
        mock_db.commit = AsyncMock()

        sol_content = b"pragma solidity ^0.8.0;\ncontract Token {}"
        resp = client.post(
            "/api/v1/projects",
            files={"files": ("Token.sol", sol_content, "text/plain")},
            data={"name": "Test Project"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_proj")
    @patch("os.makedirs")
    @patch("builtins.open", MagicMock())
    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_upload_returns_project_response(
        self, mock_realpath, mock_makedirs, mock_get_dir, mock_process, app_client
    ):
        client, mock_db = app_client

        async def fake_refresh(p):
            p.id = 42
            p.name = "MyProject"
            p.status = "uploaded"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)
        mock_db.commit = AsyncMock()

        sol_content = b"pragma solidity ^0.8.0;"
        resp = client.post(
            "/api/v1/projects",
            files={"files": ("Contract.sol", sol_content, "text/plain")},
            data={"name": "MyProject"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "MyProject"
        assert data["status"] == "uploaded"


# ─── Project Files ────────────────────────────────────────────────

class TestProjectFiles:
    """Tests for GET /api/v1/projects/{id}/files."""

    def test_list_files_for_existing_project(self, app_client):
        client, mock_db = app_client

        project = MagicMock()
        project.id = 1

        pf = MagicMock()
        pf.id = 1
        pf.file_path = "contracts/Token.sol"
        pf.status = "processed"

        mock_db.get = AsyncMock(return_value=project)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [pf]
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get("/api/v1/projects/1/files")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["file_path"] == "contracts/Token.sol"

    def test_list_files_nonexistent_project(self, app_client):
        client, mock_db = app_client
        mock_db.get = AsyncMock(return_value=None)

        resp = client.get("/api/v1/projects/999/files")
        assert resp.status_code == 404


# ─── Analysis Trigger ─────────────────────────────────────────────

class TestAnalysisTrigger:
    """Tests for POST /api/v1/projects/{id}/analyze."""

    def test_trigger_analysis_on_ready_project(self, app_client):
        from app.services.task_dispatcher import set_task_dispatcher, reset_task_dispatcher

        client, mock_db = app_client

        project = MagicMock()
        project.id = 1
        project.status = "ready"
        mock_db.get = AsyncMock(return_value=project)

        # 注入 mock dispatcher，替代旧的 patch build_analysis_pipeline
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch_analysis.return_value = "task-123"
        set_task_dispatcher(mock_dispatcher)

        try:
            resp = client.post("/api/v1/projects/1/analyze")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "started"
            assert data["task_id"] == "task-123"
            mock_dispatcher.dispatch_analysis.assert_called_once_with(1)
        finally:
            reset_task_dispatcher()

    def test_trigger_analysis_on_non_ready_project(self, app_client):
        client, mock_db = app_client

        project = MagicMock()
        project.id = 1
        project.status = "uploaded"
        mock_db.get = AsyncMock(return_value=project)

        resp = client.post("/api/v1/projects/1/analyze")
        assert resp.status_code == 409

    def test_trigger_analysis_nonexistent_project(self, app_client):
        client, mock_db = app_client
        mock_db.get = AsyncMock(return_value=None)

        resp = client.post("/api/v1/projects/999/analyze")
        assert resp.status_code == 404


# ─── Mark False Positive ─────────────────────────────────────────

class TestMarkFalsePositiveAPI:
    """Tests for POST /api/v1/detections/{id}/mark-false-positive."""

    def test_mark_fp_success(self, app_client):
        client, mock_db = app_client

        detection = MagicMock()
        detection.id = 1
        detection.detection_ref = "slither-001"
        detection.analysis_result_id = 1

        analysis_result = MagicMock()
        analysis_result.id = 1
        analysis_result.project_id = 1

        async def fake_get(model, obj_id):
            if model.__name__ == "Detection":
                return detection
            if model.__name__ == "AnalysisResult":
                return analysis_result
            return None

        mock_db.get = AsyncMock(side_effect=fake_get)

        resp = client.post(
            "/api/v1/detections/1/mark-false-positive",
            json={"user_note": "Safe pattern"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "marked"
        assert data["detection_ref"] == "slither-001"

    def test_mark_fp_detection_not_found(self, app_client):
        client, mock_db = app_client
        mock_db.get = AsyncMock(return_value=None)

        resp = client.post("/api/v1/detections/999/mark-false-positive", json={})
        assert resp.status_code == 404


# ─── Nonexistent Route ────────────────────────────────────────────

class TestNegativeCases:
    """Negative test cases for API endpoints."""

    def test_nonexistent_project_files(self, app_client):
        client, mock_db = app_client
        mock_db.get = AsyncMock(return_value=None)

        resp = client.get("/api/v1/projects/99999/files")
        assert resp.status_code == 404
