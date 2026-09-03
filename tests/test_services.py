"""Unit tests for SolidGuard service modules.

Tests:
- project_service: create_project_with_files, get_project_files, get_project_or_404
- detection_service: mark_false_positive
- analysis_service: list_analyses_filtered
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


# ─── project_service ──────────────────────────────────────────────

class TestCreateProjectWithFiles:
    """Tests for project_service.create_project_with_files."""

    @pytest.mark.asyncio
    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_project")
    @patch("builtins.open", MagicMock())
    @patch("os.makedirs")
    @patch("os.path.realpath", side_effect=lambda p, **kwargs: p)
    async def test_create_project_with_sol_file(
        self, mock_makedirs, mock_get_dir, mock_process, mock_db
    ):
        from app.services.project_service import create_project_with_files

        mock_file = MagicMock()
        mock_file.filename = "Token.sol"
        mock_file.content_type = "text/plain"
        mock_file.read = AsyncMock(return_value=b"pragma solidity ^0.8.0;")

        project = MagicMock()
        project.id = 1
        mock_db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", 1))
        mock_db.commit = AsyncMock()

        result = await create_project_with_files(mock_db, "Test", [mock_file])
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_project")
    @patch("os.makedirs")
    async def test_create_project_rejects_bad_extension(
        self, mock_makedirs, mock_get_dir, mock_process, mock_db
    ):
        """所有文件扩展名均不支持时，应删除项目并抛 422。"""
        from app.services.project_service import create_project_with_files
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = "malware.exe"
        mock_file.content_type = "application/octet-stream"

        mock_db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", 1))

        with pytest.raises(HTTPException) as exc_info:
            await create_project_with_files(mock_db, "Test", [mock_file])
        assert exc_info.value.status_code == 422
        assert "unsupported extension" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_project")
    @patch("os.makedirs")
    async def test_create_project_rejects_bad_mime(
        self, mock_makedirs, mock_get_dir, mock_process, mock_db
    ):
        """所有文件 MIME 类型均不支持时，应删除项目并抛 422。"""
        from app.services.project_service import create_project_with_files
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = "Token.sol"
        mock_file.content_type = "application/javascript"

        mock_db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", 1))

        with pytest.raises(HTTPException) as exc_info:
            await create_project_with_files(mock_db, "Test", [mock_file])
        assert exc_info.value.status_code == 422
        assert "unsupported MIME type" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_project")
    @patch("os.makedirs")
    async def test_create_project_rejects_no_filename(
        self, mock_makedirs, mock_get_dir, mock_process, mock_db
    ):
        """所有文件均缺少 filename 时，应删除项目并抛 422。"""
        from app.services.project_service import create_project_with_files
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = None

        mock_db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", 1))

        with pytest.raises(HTTPException) as exc_info:
            await create_project_with_files(mock_db, "Test", [mock_file])
        assert exc_info.value.status_code == 422
        assert "file missing filename" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.project_service.process_upload")
    @patch("app.services.project_service.get_project_dir", return_value="/tmp/test_project")
    @patch("builtins.open", MagicMock())
    @patch("os.makedirs")
    async def test_create_project_skips_bad_keeps_good(
        self, mock_makedirs, mock_get_dir, mock_process, mock_db
    ):
        """混合上传时，跳过无效文件、保留有效文件，项目正常创建。"""
        from app.services.project_service import create_project_with_files

        bad_file = MagicMock()
        bad_file.filename = "malware.exe"
        bad_file.content_type = "application/octet-stream"

        good_file = MagicMock()
        good_file.filename = "Token.sol"
        good_file.content_type = "text/plain"
        good_file.read = AsyncMock(return_value=b"pragma solidity ^0.8.0;")

        mock_db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", 1))
        mock_db.commit = AsyncMock()

        result = await create_project_with_files(mock_db, "Test", [bad_file, good_file])
        mock_db.add.assert_called_once()
        mock_process.delay.assert_called_once_with(1)


class TestGetProjectFiles:
    """Tests for project_service.get_project_files."""

    @pytest.mark.asyncio
    async def test_get_project_files_success(self, mock_db, sample_project, sample_project_file):
        from app.services.project_service import get_project_files

        mock_db.get = AsyncMock(return_value=sample_project)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_project_file]
        mock_db.execute = AsyncMock(return_value=mock_result)

        files = await get_project_files(mock_db, 1)
        assert len(files) == 1
        assert files[0].file_path == "contracts/Token.sol"

    @pytest.mark.asyncio
    async def test_get_project_files_not_found(self, mock_db):
        from app.services.project_service import get_project_files
        from fastapi import HTTPException

        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_project_files(mock_db, 999)
        assert exc_info.value.status_code == 404


class TestGetProjectOr404:
    """Tests for project_service.get_project_or_404."""

    @pytest.mark.asyncio
    async def test_get_project_or_404_found(self, mock_db, sample_project):
        from app.services.project_service import get_project_or_404

        mock_db.get = AsyncMock(return_value=sample_project)

        result = await get_project_or_404(mock_db, 1)
        assert result.name == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_or_404_not_found(self, mock_db):
        from app.services.project_service import get_project_or_404
        from fastapi import HTTPException

        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_project_or_404(mock_db, 999)
        assert exc_info.value.status_code == 404


# ─── detection_service ────────────────────────────────────────────

class TestMarkFalsePositive:
    """Tests for detection_service.mark_false_positive."""

    @pytest.mark.asyncio
    async def test_mark_false_positive_success(
        self, mock_db, sample_detection, sample_analysis_result
    ):
        from app.services.detection_service import mark_false_positive

        mock_db.get = AsyncMock(side_effect=lambda model, id: {
            1: sample_detection,
        }.get(id) if model.__name__ == "Detection" else sample_analysis_result)

        async def fake_get(model, obj_id):
            if model.__name__ == "Detection":
                return sample_detection
            if model.__name__ == "AnalysisResult":
                return sample_analysis_result
            return None

        mock_db.get = AsyncMock(side_effect=fake_get)

        result = await mark_false_positive(mock_db, 1, "Safe pattern")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_mark_false_positive_detection_not_found(self, mock_db):
        from app.services.detection_service import mark_false_positive
        from fastapi import HTTPException

        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await mark_false_positive(mock_db, 999)
        assert exc_info.value.status_code == 404
        assert "Detection" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_mark_false_positive_analysis_not_found(self, mock_db, sample_detection):
        from app.services.detection_service import mark_false_positive
        from fastapi import HTTPException

        async def fake_get(model, obj_id):
            if model.__name__ == "Detection":
                return sample_detection
            return None

        mock_db.get = AsyncMock(side_effect=fake_get)

        with pytest.raises(HTTPException) as exc_info:
            await mark_false_positive(mock_db, 1)
        assert exc_info.value.status_code == 404
        assert "Analysis result" in exc_info.value.detail


# ─── analysis_service ─────────────────────────────────────────────

class TestListAnalysesFiltered:
    """Tests for analysis_service.list_analyses_filtered."""

    @pytest.mark.asyncio
    async def test_filters_out_false_positives(self, mock_db, sample_project, sample_detection):
        from app.services.analysis_service import list_analyses_filtered

        mock_db.get = AsyncMock(return_value=sample_project)

        det_a = MagicMock()
        det_a.id = 1
        det_a.detection_ref = "ref-a"
        det_b = MagicMock()
        det_b.id = 2
        det_b.detection_ref = "ref-b"

        detections_result = MagicMock()
        detections_result.scalars.return_value.all.return_value = [det_a, det_b]

        fp_result = MagicMock()
        fp_result.scalars.return_value.all.return_value = ["ref-a"]

        call_count = 0
        async def fake_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return detections_result
            return fp_result

        mock_db.execute = AsyncMock(side_effect=fake_execute)

        result = await list_analyses_filtered(mock_db, 1)
        assert len(result) == 1
        assert result[0].detection_ref == "ref-b"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_fp(self, mock_db, sample_project, sample_detection):
        from app.services.analysis_service import list_analyses_filtered

        mock_db.get = AsyncMock(return_value=sample_project)

        detections_result = MagicMock()
        detections_result.scalars.return_value.all.return_value = [sample_detection]

        fp_result = MagicMock()
        fp_result.scalars.return_value.all.return_value = [sample_detection.detection_ref]

        call_count = 0
        async def fake_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return detections_result
            return fp_result

        mock_db.execute = AsyncMock(side_effect=fake_execute)

        result = await list_analyses_filtered(mock_db, 1)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_project_not_found(self, mock_db):
        from app.services.analysis_service import list_analyses_filtered
        from fastapi import HTTPException

        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await list_analyses_filtered(mock_db, 999)
        assert exc_info.value.status_code == 404
