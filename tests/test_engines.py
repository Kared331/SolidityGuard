"""Unit tests for SolidGuard engine modules.

Tests:
- upload engine: _is_safe_path, _scan_sol_files, Zip Slip prevention
- llm_audit engine: _parse_llm_json with various inputs
- report engine: ReportEngine.execute with mocks
"""

import json
import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Pre-mock problematic modules that fail on Python 3.9 or lack DB drivers
for mod_name in [
    "chromadb", "app.services.chroma_client",
    "app.services.embedding", "app.services.llm_client",
    "psycopg2",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Now safe to import app modules
from app.services.engine.upload import _is_safe_path, _scan_sol_files, UploadEngine
from app.services.engine.llm_audit import _parse_llm_json, _sanitize_source_code


# ─── Upload Engine: _is_safe_path ─────────────────────────────────

class TestIsSafePath:
    """Tests for upload._is_safe_path — Zip Slip prevention logic."""

    def test_safe_relative_path(self):
        assert _is_safe_path("/tmp/project", "contracts/Token.sol") is True

    def test_safe_nested_path(self):
        assert _is_safe_path("/tmp/project", "a/b/c/file.sol") is True

    def test_safe_simple_filename(self):
        assert _is_safe_path("/tmp/project", "file.txt") is True

    def test_unsafe_dot_dot_escape(self):
        assert _is_safe_path("/tmp/project", "../../etc/passwd") is False

    def test_unsafe_deep_dot_dot(self):
        assert _is_safe_path("/tmp/project", "a/../../etc/passwd") is False

    def test_unsafe_dot_dot_at_start(self):
        assert _is_safe_path("/tmp/project", "../evil.txt") is False


# ─── Upload Engine: _scan_sol_files ──────────────────────────────

class TestScanSolFiles:
    """Tests for upload._scan_sol_files."""

    def test_finds_sol_files(self, tmp_path):
        (tmp_path / "Token.sol").write_text("pragma solidity ^0.8.0;")
        (tmp_path / "Helper.sol").write_text("// helper")
        (tmp_path / "readme.txt").write_text("not solidity")

        result = _scan_sol_files(str(tmp_path))
        assert len(result) == 2
        names = {os.path.basename(r) for r in result}
        assert "Token.sol" in names
        assert "Helper.sol" in names

    def test_finds_nested_sol_files(self, tmp_path):
        sub = tmp_path / "contracts"
        sub.mkdir()
        (sub / "Deep.sol").write_text("pragma solidity ^0.8.0;")

        result = _scan_sol_files(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("Deep.sol")

    def test_empty_directory(self, tmp_path):
        result = _scan_sol_files(str(tmp_path))
        assert result == []

    def test_ignores_non_sol_files(self, tmp_path):
        (tmp_path / "readme.md").write_text("# readme")
        (tmp_path / "data.json").write_text("{}")

        result = _scan_sol_files(str(tmp_path))
        assert result == []


# ─── Upload Engine: Zip Slip Prevention ──────────────────────────

class TestZipSlipPrevention:
    """Integration test: create a malicious zip and verify extraction blocks it."""

    def test_malicious_zip_entry_blocked(self, tmp_path):
        """Create a zip with ../../evil.txt and verify _is_safe_path blocks it."""
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("../../evil.txt", "pwned")

        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for member in zf.infolist():
                assert _is_safe_path(str(tmp_path), member.filename) is False

    def test_safe_zip_entry_allowed(self, tmp_path):
        """Create a zip with safe paths and verify they pass."""
        zip_path = tmp_path / "safe.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("contracts/Token.sol", "pragma solidity ^0.8.0;")
            zf.writestr("src/utils.sol", "// utils")

        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for member in zf.infolist():
                assert _is_safe_path(str(tmp_path), member.filename) is True

    def test_execute_blocks_malicious_zip(self, tmp_path):
        """UploadEngine.execute should skip malicious zip entries."""
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("../../evil.txt", "pwned")
            zf.writestr("safe.sol", "pragma solidity ^0.8.0;")

        engine = UploadEngine()
        result = engine.execute(project_id=1, project_dir=str(tmp_path))

        evil_path = tmp_path / "evil.txt"
        assert not evil_path.exists(), "Zip Slip file should not have been extracted"
        assert result["count"] == 1
        assert any("safe.sol" in f for f in result["sol_files"])


# ─── LLM Audit Engine: _parse_llm_json ──────────────────────────

class TestParseLlmJson:
    """Tests for llm_audit._parse_llm_json — multi-strategy JSON parser."""

    def test_valid_json_array(self):
        data = [{"vulnerability": "reentrancy", "severity": "high"}]
        result = _parse_llm_json(json.dumps(data))
        assert result == data

    def test_markdown_wrapped_json(self):
        data = [{"vulnerability": "overflow", "severity": "medium"}]
        text = f"```json\n{json.dumps(data)}\n```"
        result = _parse_llm_json(text)
        assert result == data

    def test_markdown_no_language_tag(self):
        data = [{"vulnerability": "xss"}]
        text = f"```\n{json.dumps(data)}\n```"
        result = _parse_llm_json(text)
        assert result == data

    def test_bare_json_with_surrounding_text(self):
        data = [{"vulnerability": "sql_injection"}]
        text = f"Here are the findings:\n{json.dumps(data)}\nEnd of report."
        result = _parse_llm_json(text)
        assert result == data

    def test_invalid_text_returns_none(self):
        result = _parse_llm_json("This is not JSON at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_llm_json("")
        assert result is None

    def test_whitespace_only_returns_none(self):
        result = _parse_llm_json("   \n\t  ")
        assert result is None

    def test_json_object_returns_none(self):
        """A JSON object (not array) should return None since the parser expects arrays."""
        result = _parse_llm_json('{"key": "value"}')
        assert result is None

    def test_nested_markdown_with_extra_text(self):
        data = [{"finding": "weak_randomness"}]
        text = f"I analyzed the code and found:\n\n```json\n{json.dumps(data)}\n```\n\nPlease fix these."
        result = _parse_llm_json(text)
        assert result == data

    def test_empty_json_array(self):
        result = _parse_llm_json("[]")
        assert result == []


# ─── LLM Audit Engine: _sanitize_source_code ────────────────────

class TestSanitizeSourceCode:
    """Tests for llm_audit._sanitize_source_code."""

    def test_normal_code_unchanged(self):
        code = "pragma solidity ^0.8.0;\ncontract Token {}"
        result = _sanitize_source_code(code)
        assert result == code

    def test_long_code_truncated(self):
        code = "a" * 10000
        result = _sanitize_source_code(code)
        assert len(result) < 10000
        assert "truncated" in result

    def test_strips_non_printable(self):
        code = "safe code\x00\x01\x02 here"
        result = _sanitize_source_code(code)
        assert "\x00" not in result
        assert "safe code" in result

    def test_preserves_newlines_and_tabs(self):
        code = "line1\nline2\tindented"
        result = _sanitize_source_code(code)
        assert "\n" in result
        assert "\t" in result


# ─── Report Engine ───────────────────────────────────────────────

class TestReportEngine:
    """Tests for report.ReportEngine.execute with mocked dependencies."""

    def test_execute_word_format(self):
        """ReportEngine.execute with word format generates docx path."""
        # Mock the report_generator module functions
        mock_aggregate = MagicMock(return_value={
            "slither_findings": [{"check": "reentrancy"}],
            "fuzzing_findings": [],
            "llm_findings": [],
        })
        mock_polish = MagicMock(return_value={
            "slither_findings": [{"check": "reentrancy"}],
            "fuzzing_findings": [],
            "llm_findings": [],
        })
        mock_word = MagicMock(return_value="/reports/1/report.docx")

        with patch.dict("sys.modules", {
            "app.services.report_generator": MagicMock(
                aggregate_findings=mock_aggregate,
                polish_with_llm=mock_polish,
                generate_word=mock_word,
            ),
        }):
            # Re-import to pick up mocked modules
            if "app.services.engine.report" in sys.modules:
                del sys.modules["app.services.engine.report"]
            from app.services.engine.report import ReportEngine

            engine = ReportEngine()
            result = engine.execute(project_id=1, output_format="word", session=MagicMock())

            assert result["total_findings"] == 1
            assert "word" in result["file_paths"]
            mock_word.assert_called_once()

    def test_execute_html_format(self):
        """ReportEngine.execute with html format generates html path."""
        mock_aggregate = MagicMock(return_value={
            "slither_findings": [],
            "fuzzing_findings": [],
            "llm_findings": [],
        })
        mock_polish = MagicMock(return_value={
            "slither_findings": [],
            "fuzzing_findings": [],
            "llm_findings": [],
        })
        mock_html = MagicMock(return_value="/reports/1/report.html")

        with patch.dict("sys.modules", {
            "app.services.report_generator": MagicMock(
                aggregate_findings=mock_aggregate,
                polish_with_llm=mock_polish,
                generate_html=mock_html,
            ),
        }):
            if "app.services.engine.report" in sys.modules:
                del sys.modules["app.services.engine.report"]
            from app.services.engine.report import ReportEngine

            engine = ReportEngine()
            result = engine.execute(project_id=1, output_format="html", session=MagicMock())

            assert "html" in result["file_paths"]
            assert result["total_findings"] == 0
            mock_html.assert_called_once()

    def test_execute_pdf_format(self):
        """ReportEngine.execute with pdf format generates both html and pdf paths."""
        mock_aggregate = MagicMock(return_value={
            "slither_findings": [],
            "fuzzing_findings": [],
            "llm_findings": [],
        })
        mock_polish = MagicMock(return_value={
            "slither_findings": [],
            "fuzzing_findings": [],
            "llm_findings": [],
        })
        mock_html = MagicMock(return_value="/reports/1/report.html")
        mock_pdf = MagicMock(return_value="/reports/1/report.pdf")

        with patch.dict("sys.modules", {
            "app.services.report_generator": MagicMock(
                aggregate_findings=mock_aggregate,
                polish_with_llm=mock_polish,
                generate_html=mock_html,
                generate_pdf=mock_pdf,
            ),
        }):
            if "app.services.engine.report" in sys.modules:
                del sys.modules["app.services.engine.report"]
            from app.services.engine.report import ReportEngine

            engine = ReportEngine()
            result = engine.execute(project_id=1, output_format="pdf", session=MagicMock())

            assert "html" in result["file_paths"]
            assert "pdf" in result["file_paths"]
            mock_html.assert_called_once()
            mock_pdf.assert_called_once()

    def test_execute_total_findings_counted(self):
        """ReportEngine counts findings from all three sources."""
        mock_aggregate = MagicMock(return_value={
            "slither_findings": [{"a": 1}, {"b": 2}],
            "fuzzing_findings": [{"c": 3}],
            "llm_findings": [{"d": 4}, {"e": 5}, {"f": 6}],
        })
        mock_polish = MagicMock(return_value=mock_aggregate.return_value)

        with patch.dict("sys.modules", {
            "app.services.report_generator": MagicMock(
                aggregate_findings=mock_aggregate,
                polish_with_llm=mock_polish,
            ),
        }):
            if "app.services.engine.report" in sys.modules:
                del sys.modules["app.services.engine.report"]
            from app.services.engine.report import ReportEngine

            engine = ReportEngine()
            result = engine.execute(project_id=1, output_format="html", session=MagicMock())

            assert result["total_findings"] == 6
