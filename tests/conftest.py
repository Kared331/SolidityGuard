"""Shared fixtures for SolidGuard Sprint D tests.

Provides mock database sessions, sample model objects, and a FastAPI
TestClient with dependencies overridden for isolated unit/integration testing.
"""

import atexit
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Ensure backend package is importable
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Set environment variables used by ${...} references in the config file
os.environ.setdefault("API_KEY", "test-api-key-12345")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

# Create a temporary JSON config file for tests
_test_config = {
    "app": {
        "apiKey": "${API_KEY}",
        "port": 8000,
        "maxUploadSizeMb": 50,
        "cleanupDays": 30,
        "logLevel": "DEBUG",
        "corsOrigins": "*",
        "rateLimit": "1000/minute",
    },
    "database": {
        "url": "${DATABASE_URL}",
        "poolSize": 5,
        "maxOverflow": 10,
        "poolRecycle": 3600,
    },
    "redis": {
        "url": "redis://localhost:6379/0",
    },
    "rag": {
        "chromaPersistDir": "./test_chroma_data",
        "topK": 3,
    },
    "providers": {
        "default": {
            "apiKey": "sk-test",
            "baseUrl": "https://api.openai.com/v1",
            "api": "openai",
            "defaultModel": "gpt-4o",
            "models": [
                {
                    "id": "gpt-4o",
                    "name": "GPT-4o",
                    "maxTokens": 4096,
                    "contextWindow": 128000,
                }
            ],
        },
        "embedding": {
            "apiKey": "sk-test",
            "baseUrl": "https://api.openai.com/v1",
            "api": "openai",
            "defaultModel": "text-embedding-3-small",
            "models": [
                {
                    "id": "text-embedding-3-small",
                    "name": "Text Embedding 3 Small",
                    "maxTokens": 8191,
                    "contextWindow": 8191,
                }
            ],
        },
    },
}

_test_config_file = tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", delete=False,
)
json.dump(_test_config, _test_config_file)
_test_config_file.close()
os.environ["SOLIDGUARD_CONFIG"] = _test_config_file.name


def _cleanup_test_config():
    """Remove the temporary config file on process exit."""
    try:
        os.unlink(_test_config_file.name)
    except OSError:
        pass


atexit.register(_cleanup_test_config)


# ─── Mock problematic modules before any app imports ──────────────
# Python 3.9 cannot parse `chromadb.Client | None` syntax in chroma_client.py.
# We inject mock modules into sys.modules so imports succeed.

_chroma_mock = MagicMock()
_chroma_mock.Client = MagicMock
_chroma_mock.Collection = MagicMock
_chroma_mock.PersistentClient = MagicMock
sys.modules.setdefault("chromadb", _chroma_mock)

_embedding_mock = MagicMock()
_embedding_mock.get_embedding = MagicMock(return_value=[0.1] * 384)
sys.modules.setdefault("app.services.embedding", _embedding_mock)

_llm_client_mock = MagicMock()
_llm_client_mock.chat_completion = MagicMock(return_value=("[]", {"total_tokens": 100}))
sys.modules.setdefault("app.llm.sync_wrapper", _llm_client_mock)

_chroma_client_mock = MagicMock()
_chroma_client_mock.get_vulnerability_collection = MagicMock()
_chroma_client_mock.get_chroma_client = MagicMock()
sys.modules.setdefault("app.services.chroma_client", _chroma_client_mock)

# psycopg2 may not be installed; mock it for database module imports
_psycopg2_mock = MagicMock()
sys.modules.setdefault("psycopg2", _psycopg2_mock)

_weasyprint_mock = MagicMock()
sys.modules.setdefault("weasyprint", _weasyprint_mock)

_docx_mock = MagicMock()
sys.modules.setdefault("docx", _docx_mock)


# ─── Mock Database Session ────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Return an AsyncMock that behaves like an AsyncSession."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ─── Sample Model Objects ─────────────────────────────────────────

@pytest.fixture
def sample_project():
    """Return a mock Project object."""
    from app.models.project import Project

    project = MagicMock(spec=Project)
    project.id = 1
    project.name = "Test Project"
    project.status = "uploaded"
    project.files = []
    project.analyses = []
    return project


@pytest.fixture
def sample_ready_project():
    """Return a mock Project in READY state."""
    from app.models.project import Project

    project = MagicMock(spec=Project)
    project.id = 2
    project.name = "Ready Project"
    project.status = "ready"
    project.files = []
    project.analyses = []
    return project


@pytest.fixture
def sample_project_file():
    """Return a mock ProjectFile object."""
    from app.models.project import ProjectFile

    pf = MagicMock(spec=ProjectFile)
    pf.id = 1
    pf.project_id = 1
    pf.file_path = "contracts/Token.sol"
    pf.status = "processed"
    return pf


@pytest.fixture
def sample_analysis_result():
    """Return a mock AnalysisResult object."""
    from app.models.analysis import AnalysisResult

    ar = MagicMock(spec=AnalysisResult)
    ar.id = 1
    ar.project_id = 1
    ar.analyzer = "slither"
    ar.result_json = {"detectors": []}
    return ar


@pytest.fixture
def sample_detection():
    """Return a mock Detection object."""
    from app.models.analysis import Detection

    det = MagicMock(spec=Detection)
    det.id = 1
    det.analysis_result_id = 1
    det.detection_ref = "slither-001"
    det.check_name = "reentrancy-eth"
    det.description = "Reentrancy vulnerability"
    det.impact = "High"
    det.confidence = "Medium"
    det.element_json = None
    return det


@pytest.fixture
def sample_false_positive():
    """Return a mock FalsePositiveFeedback object."""
    from app.models.feedback import FalsePositiveFeedback

    fp = MagicMock(spec=FalsePositiveFeedback)
    fp.id = 1
    fp.project_id = 1
    fp.detection_ref = "slither-001"
    fp.user_note = "False positive - safe pattern"
    return fp


@pytest.fixture
def sample_report():
    """Return a mock Report object."""
    from app.models.report import Report

    report = MagicMock(spec=Report)
    report.id = 1
    report.project_id = 1
    report.title = "SolidiGuard Audit Report - Project 1"
    report.content_json = {"findings": []}
    report.file_paths = {"html": "/reports/1/report.html"}
    return report


# ─── FastAPI TestClient ───────────────────────────────────────────

@pytest.fixture
def test_client():
    """Return a FastAPI TestClient with DB dependency overridden."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import get_db

    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_with_db(mock_db):
    """Return a (TestClient, mock_db) pair for tests that need the session reference."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import get_db

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, mock_db
    app.dependency_overrides.clear()
