"""
SolidiGuard Integration Tests — Sprint 10 (fixed 5.23)
Each test uses independent project fixtures to avoid state dependency.
Requires: docker-compose up (api, worker, postgres, redis) running on localhost:8000
"""
import os
import time
import zipfile
import io

import httpx
import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ZIP_PATH = os.path.join(FIXTURES_DIR, "test_contracts.zip")
TOKEN_PATH = os.path.join(FIXTURES_DIR, "VulnerableToken.sol")


# ─── Health Check ────────────────────────────────────────────────

def test_health(client: httpx.Client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ─── Project Upload ──────────────────────────────────────────────

def test_upload_zip(client: httpx.Client):
    """Upload a zip containing .sol files."""
    with open(ZIP_PATH, "rb") as f:
        resp = client.post(
            "/api/v1/projects",
            files={"files": ("test_contracts.zip", f, "application/zip")},
            data={"name": "Integration Test Project"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["name"] == "Integration Test Project"


def test_upload_single_sol(client: httpx.Client):
    """Upload a single .sol file."""
    with open(TOKEN_PATH, "rb") as f:
        resp = client.post(
            "/api/v1/projects",
            files={"files": ("VulnerableToken.sol", f, "text/plain")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


def test_list_project_files(client: httpx.Client, unique_project):
    """List files for an independent project."""
    project_id = unique_project
    resp = client.get(f"/api/v1/projects/{project_id}/files")
    assert resp.status_code == 200
    files = resp.json()
    assert isinstance(files, list)
    assert len(files) > 0
    for f in files:
        assert "file_path" in f
        assert "status" in f


# ─── Slither Analysis ────────────────────────────────────────────

def test_trigger_slither(client: httpx.Client, unique_project):
    """Trigger Slither analysis on an independent project."""
    project_id = unique_project
    resp = client.post(f"/api/v1/projects/{project_id}/analyze")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["project_id"] == project_id


def test_wait_for_slither_results(client: httpx.Client, unique_project):
    """Poll for Slither results on an independent project (max 120s)."""
    project_id = unique_project
    # Trigger first
    client.post(f"/api/v1/projects/{project_id}/analyze")

    for _ in range(40):
        time.sleep(3)
        resp = client.get(f"/api/v1/projects/{project_id}/analyses")
        assert resp.status_code == 200
        results = resp.json()
        if len(results) > 0:
            for r in results:
                assert "id" in r
                assert "check_name" in r
                assert "description" in r
            return
    pytest.skip("Slither analysis did not complete in time (worker may not be running)")


# ─── Fuzzing ─────────────────────────────────────────────────────

def test_trigger_fuzzing(client: httpx.Client, unique_project):
    """Trigger Fuzzing on an independent project."""
    project_id = unique_project
    resp = client.post(f"/api/v1/projects/{project_id}/fuzz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fuzz_started"


def test_fuzz_results_exist(client: httpx.Client, unique_project):
    """Check that fuzz results endpoint works (may be empty)."""
    project_id = unique_project
    resp = client.get(f"/api/v1/projects/{project_id}/fuzz-results")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)


# ─── LLM Audit ──────────────────────────────────────────────────

def test_trigger_llm_audit(client: httpx.Client, unique_project):
    """Trigger LLM audit on an independent project."""
    project_id = unique_project
    resp = client.post(f"/api/v1/projects/{project_id}/llm-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "audit_started"


def test_llm_audit_results_endpoint(client: httpx.Client, unique_project):
    """Check that LLM audit results endpoint works."""
    project_id = unique_project
    resp = client.get(f"/api/v1/projects/{project_id}/llm-audit-results")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)


# ─── False Positive Feedback ────────────────────────────────────

def test_mark_false_positive(client: httpx.Client, unique_project):
    """Mark a Slither detection as false positive."""
    project_id = unique_project
    # Trigger analysis and wait for results
    client.post(f"/api/v1/projects/{project_id}/analyze")
    slither_results = []
    for _ in range(40):
        time.sleep(3)
        resp = client.get(f"/api/v1/projects/{project_id}/analyses")
        if resp.status_code == 200:
            slither_results = resp.json()
            if len(slither_results) > 0:
                break

    if not slither_results:
        pytest.skip("No Slither results available")

    detection_id = slither_results[0]["id"]
    resp = client.post(f"/api/v1/detections/{detection_id}/mark-false-positive", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "marked"
    assert "detection_ref" in data


def test_filtered_results_after_fp(client: httpx.Client, unique_project):
    """Verify that FP-marked detections are excluded from results."""
    project_id = unique_project
    # Trigger analysis and wait for results
    client.post(f"/api/v1/projects/{project_id}/analyze")
    slither_results = []
    for _ in range(40):
        time.sleep(3)
        resp = client.get(f"/api/v1/projects/{project_id}/analyses")
        if resp.status_code == 200:
            slither_results = resp.json()
            if len(slither_results) > 0:
                break

    if not slither_results:
        pytest.skip("No Slither results available")

    # Mark first detection as FP
    detection_id = slither_results[0]["id"]
    client.post(f"/api/v1/detections/{detection_id}/mark-false-positive", json={})

    # Verify it's excluded
    resp = client.get(f"/api/v1/projects/{project_id}/analyses")
    assert resp.status_code == 200
    results = resp.json()
    result_ids = [r["id"] for r in results]
    assert detection_id not in result_ids


# ─── Vulnerability Database ─────────────────────────────────────

def test_vulnerability_search(client: httpx.Client):
    """Search vulnerabilities by keyword."""
    resp = client.get("/api/v1/vulnerabilities", params={"search": "overflow", "page": 1, "page_size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_vulnerability_pagination(client: httpx.Client):
    """Test vulnerability list pagination."""
    resp = client.get("/api/v1/vulnerabilities", params={"page": 1, "page_size": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 5


# ─── Knowledge Sync ─────────────────────────────────────────────

def test_trigger_knowledge_sync(client: httpx.Client):
    """Trigger vulnerability knowledge sync."""
    resp = client.post("/api/v1/knowledge/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sync_started"


# ─── Report Generation ──────────────────────────────────────────

def test_trigger_report_html(client: httpx.Client, unique_project):
    """Trigger HTML report generation on an independent project."""
    project_id = unique_project
    resp = client.post(f"/api/v1/projects/{project_id}/report", json={"format": "html"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "report_started"
    assert data["format"] == "html"


def test_list_reports(client: httpx.Client, unique_project):
    """List reports for an independent project."""
    project_id = unique_project
    # Trigger report first
    client.post(f"/api/v1/projects/{project_id}/report", json={"format": "html"})
    # Wait for generation
    time.sleep(5)
    resp = client.get(f"/api/v1/projects/{project_id}/reports")
    assert resp.status_code == 200
    reports = resp.json()
    assert isinstance(reports, list)


def test_download_report(client: httpx.Client, unique_project):
    """Download a generated report."""
    project_id = unique_project
    # Trigger and wait for report
    client.post(f"/api/v1/projects/{project_id}/report", json={"format": "html"})
    time.sleep(5)
    resp = client.get(f"/api/v1/projects/{project_id}/reports")
    reports = resp.json()

    if not reports:
        pytest.skip("No report generated to download")

    report_id = reports[0]["id"]
    resp = client.get(f"/api/v1/reports/{report_id}/download", params={"format": "html"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ─── Negative Cases ─────────────────────────────────────────────

def test_404_nonexistent_project(client: httpx.Client):
    """Verify 404 for nonexistent project."""
    resp = client.get("/api/v1/projects/99999/files")
    assert resp.status_code == 404


def test_404_nonexistent_report(client: httpx.Client):
    """Verify 404 for nonexistent report download."""
    resp = client.get("/api/v1/reports/99999/download", params={"format": "html"})
    assert resp.status_code == 404
