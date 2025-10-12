"""Tests for job_scheduler_sse_api.py example."""

import asyncio
import json
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app() -> AsyncGenerator[FastAPI, None]:
    """Load job_scheduler_sse_api.py app and trigger lifespan."""
    import sys
    from pathlib import Path

    examples_dir = Path(__file__).parent.parent / "examples"
    sys.path.insert(0, str(examples_dir))

    from job_scheduler_sse_api import app as example_app  # type: ignore[import-not-found]

    async with example_app.router.lifespan_context(example_app):
        yield example_app

    sys.path.remove(str(examples_dir))


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health endpoint is available."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_submit_slow_compute_job(client: AsyncClient):
    """Test submitting slow computation job."""
    response = await client.post("/api/v1/slow-compute", json={"steps": 10})
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert "stream_url" in data
    assert data["stream_url"].startswith("/api/v1/jobs/")
    assert data["stream_url"].endswith("/$stream")
    assert "Location" in response.headers


@pytest.mark.asyncio
async def test_slow_compute_validation(client: AsyncClient):
    """Test request validation for slow compute."""
    # Too few steps
    response = await client.post("/api/v1/slow-compute", json={"steps": 5})
    assert response.status_code == 422

    # Too many steps
    response = await client.post("/api/v1/slow-compute", json={"steps": 100})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sse_streaming_slow_compute(client: AsyncClient):
    """Test SSE streaming for slow computation job."""
    # Submit job
    response = await client.post("/api/v1/slow-compute", json={"steps": 10})
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Stream status updates
    events = []
    async with client.stream("GET", f"/api/v1/jobs/{job_id}/$stream?poll_interval=0.1") as stream_response:
        assert stream_response.status_code == 200
        assert stream_response.headers["content-type"] == "text/event-stream; charset=utf-8"

        async for line in stream_response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                events.append(data)
                if data["status"] == "completed":
                    break

    # Verify we got multiple events showing progress
    assert len(events) >= 1
    assert events[-1]["status"] == "completed"
    # artifact_id is null because task returns SlowComputeResult, not ULID
    assert events[-1]["artifact_id"] is None


@pytest.mark.asyncio
async def test_job_completes_successfully(client: AsyncClient):
    """Test that job completes successfully."""
    # Submit and wait
    response = await client.post("/api/v1/slow-compute", json={"steps": 10})
    job_id = response.json()["job_id"]

    # Wait for completion via polling
    job = None
    for _ in range(30):
        job_response = await client.get(f"/api/v1/jobs/{job_id}")
        job = job_response.json()
        if job["status"] == "completed":
            break
        await asyncio.sleep(0.5)

    # Verify job completed
    assert job is not None
    assert job["status"] == "completed"
    assert job["finished_at"] is not None


@pytest.mark.asyncio
async def test_openapi_schema_includes_endpoints(client: AsyncClient):
    """Test OpenAPI schema includes slow-compute and SSE endpoints."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    paths = schema["paths"]
    assert "/api/v1/slow-compute" in paths
    assert "/api/v1/jobs/{job_id}/$stream" in paths
