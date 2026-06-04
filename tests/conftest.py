"""Test configuration with API key support (1.3)."""

import os
import pytest
import httpx


API_BASE = os.environ.get("TEST_API_BASE", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "")


@pytest.fixture(scope="session")
def base_url():
    return API_BASE


@pytest.fixture(scope="session")
def client(base_url):
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    with httpx.Client(base_url=base_url, timeout=60.0, headers=headers) as c:
        yield c


@pytest.fixture()
def unique_project(client: httpx.Client):
    """Create a fresh project for each test, yield its ID, then clean up (5.23)."""
    import zipfile
    import io

    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    zip_path = os.path.join(fixtures_dir, "test_contracts.zip")

    with open(zip_path, "rb") as f:
        resp = client.post(
            "/api/v1/projects",
            files={"files": ("test_contracts.zip", f, "application/zip")},
            data={"name": "Test Project"},
        )
    assert resp.status_code == 200, f"Failed to create project: {resp.text}"
    project_id = resp.json()["id"]

    yield project_id
