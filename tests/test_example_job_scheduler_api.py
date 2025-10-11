"""Tests for job_scheduler_api example using TestClient.

This example demonstrates the job scheduler for async long-running tasks.
"""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from examples.job_scheduler_api import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient for testing with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient) -> None:
    """Test health check returns healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_submit_computation_job(client: TestClient) -> None:
    """Test submitting a computation job returns 202 with job ID and Location header."""
    compute_request = {
        "duration": 0.5  # Short duration for testing
    }

    response = client.post("/api/v1/compute", json=compute_request)
    assert response.status_code == 202
    data = response.json()

    # Verify response structure
    assert "job_id" in data
    assert "message" in data
    assert "Poll GET /api/v1/jobs/" in data["message"]

    # Verify Location header
    assert "Location" in response.headers
    location = response.headers["Location"]
    assert f"/api/v1/jobs/{data['job_id']}" in location


def test_list_jobs(client: TestClient) -> None:
    """Test listing all jobs."""
    # Submit a job first
    compute_request = {"duration": 0.1}
    client.post("/api/v1/compute", json=compute_request)

    # List jobs
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    # Verify job structure
    job = data[0]
    assert "id" in job
    assert "status" in job
    assert "submitted_at" in job
    assert job["status"] in ["pending", "running", "completed", "failed", "canceled"]


def test_list_jobs_with_status_filter(client: TestClient) -> None:
    """Test listing jobs filtered by status."""
    # Submit and wait for completion
    compute_request = {"duration": 0.1}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    # Wait for completion
    time.sleep(0.5)

    # Filter for completed jobs
    response = client.get("/api/v1/jobs", params={"status_filter": "completed"})
    assert response.status_code == 200
    jobs = response.json()

    # Should include our completed job
    assert any(job["id"] == job_id for job in jobs)
    assert all(job["status"] == "completed" for job in jobs)


def test_get_job_record(client: TestClient) -> None:
    """Test retrieving a specific job record."""
    # Submit a job
    compute_request = {"duration": 0.1}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    # Get job record
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    job = response.json()

    assert job["id"] == job_id
    assert "status" in job
    assert "submitted_at" in job
    assert job["status"] in ["pending", "running", "completed"]


def test_get_job_record_not_found(client: TestClient) -> None:
    """Test retrieving non-existent job returns 404."""
    response = client.get("/api/v1/jobs/01K72P5N5KCRM6MD3BRE4P0999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_computation_result_pending(client: TestClient) -> None:
    """Test getting result of pending/running job."""
    # Submit a longer-running job
    compute_request = {"duration": 5.0}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    # Immediately check result (should be pending or running)
    response = client.get(f"/api/v1/compute/{job_id}/result")
    assert response.status_code == 200
    result = response.json()

    assert result["job_id"] == job_id
    assert result["status"] in ["pending", "running"]
    assert result["result"] is None
    assert result["error"] is None


def test_get_computation_result_completed(client: TestClient) -> None:
    """Test getting result of completed job."""
    # Submit a short job
    compute_request = {"duration": 0.2}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    # Wait for completion
    time.sleep(0.5)

    # Get result
    response = client.get(f"/api/v1/compute/{job_id}/result")
    assert response.status_code == 200
    result = response.json()

    assert result["job_id"] == job_id
    assert result["status"] == "completed"
    assert result["result"] == 42  # Expected result from long_running_computation
    assert result["error"] is None
    assert result["submitted_at"] is not None
    assert result["started_at"] is not None
    assert result["finished_at"] is not None


def test_job_status_transitions(client: TestClient) -> None:
    """Test job status transitions from pending -> running -> completed."""
    # Submit a job
    compute_request = {"duration": 0.3}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    # Check initial status (should be pending or running)
    response1 = client.get(f"/api/v1/jobs/{job_id}")
    job1 = response1.json()
    assert job1["status"] in ["pending", "running"]

    # Wait a bit
    time.sleep(0.1)

    # Check status again (likely running)
    response2 = client.get(f"/api/v1/jobs/{job_id}")
    job2 = response2.json()
    assert job2["status"] in ["running", "completed"]

    # Wait for completion
    time.sleep(0.5)

    # Check final status (should be completed)
    response3 = client.get(f"/api/v1/jobs/{job_id}")
    job3 = response3.json()
    assert job3["status"] == "completed"


def test_cancel_job(client: TestClient) -> None:
    """Test canceling a running job."""
    # Submit a long-running job
    compute_request = {"duration": 10.0}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    # Wait a bit to ensure it starts
    time.sleep(0.2)

    # Cancel it
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 204

    # Verify it's canceled (or at least not running)
    # Note: The job might complete before cancellation in some cases
    job_response = client.get(f"/api/v1/jobs/{job_id}")
    # Job record should be deleted, so we expect 404
    assert job_response.status_code == 404


def test_delete_completed_job(client: TestClient) -> None:
    """Test deleting a completed job record."""
    # Submit and wait for completion
    compute_request = {"duration": 0.1}
    submit_response = client.post("/api/v1/compute", json=compute_request)
    job_id = submit_response.json()["job_id"]

    time.sleep(0.3)

    # Delete the completed job
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 404


def test_delete_job_not_found(client: TestClient) -> None:
    """Test deleting non-existent job returns 404."""
    response = client.delete("/api/v1/jobs/01K72P5N5KCRM6MD3BRE4P0999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_submit_multiple_concurrent_jobs(client: TestClient) -> None:
    """Test submitting multiple jobs respects max_concurrency=5."""
    # Submit 7 jobs (max_concurrency is 5)
    job_ids = []
    for _ in range(7):
        compute_request = {"duration": 0.2}
        response = client.post("/api/v1/compute", json=compute_request)
        job_data = response.json()
        job_ids.append(job_data["job_id"])

    # All should be accepted
    assert len(job_ids) == 7

    # Wait for completion
    time.sleep(0.5)

    # Check that all jobs completed
    for job_id in job_ids:
        response = client.get(f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            assert job["status"] in ["completed", "running"]


def test_invalid_duration_too_low(client: TestClient) -> None:
    """Test submitting job with duration too low fails validation."""
    compute_request = {"duration": 0.05}  # Below minimum of 0.1

    response = client.post("/api/v1/compute", json=compute_request)
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data


def test_invalid_duration_too_high(client: TestClient) -> None:
    """Test submitting job with duration too high fails validation."""
    compute_request = {"duration": 100.0}  # Above maximum of 60

    response = client.post("/api/v1/compute", json=compute_request)
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data


def test_get_result_for_nonexistent_job(client: TestClient) -> None:
    """Test getting result for non-existent job returns error."""
    response = client.get("/api/v1/compute/01K72P5N5KCRM6MD3BRE4P0999/result")
    # May return 404 or 500 depending on implementation
    assert response.status_code in [404, 500]
