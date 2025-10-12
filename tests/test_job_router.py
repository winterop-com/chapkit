"""Tests for job router endpoints."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import ulid
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chapkit.api import ServiceBuilder, ServiceInfo

ULID = ulid.ULID


@pytest.fixture
async def app() -> AsyncGenerator[FastAPI, None]:
    """Create FastAPI app with job router and trigger lifespan."""
    info = ServiceInfo(display_name="Test Service")
    app_instance = ServiceBuilder(info=info).with_jobs().build()

    # Manually trigger lifespan
    async with app_instance.router.lifespan_context(app_instance):
        yield app_instance


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True) as ac:
        yield ac


class TestJobRouter:
    """Test job router endpoints."""

    @pytest.mark.asyncio
    async def test_get_jobs_empty(self, client: AsyncClient):
        """Test GET /api/v1/jobs returns empty list initially."""
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert jobs == []

    @pytest.mark.asyncio
    async def test_get_jobs_after_adding(self, client: AsyncClient, app: FastAPI):
        """Test GET /api/v1/jobs returns jobs after adding them."""
        # Get scheduler and add a job
        scheduler = app.state.scheduler

        async def task():
            return "result"

        job_id = await scheduler.add_job(task)
        await scheduler.wait(job_id)

        # Get jobs
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["id"] == str(job_id)
        assert jobs[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_jobs_filtered_by_status(self, client: AsyncClient, app: FastAPI):
        """Test GET /api/v1/jobs?status_filter=completed filters jobs."""
        scheduler = app.state.scheduler

        async def quick_task():
            return "done"

        async def slow_task():
            await asyncio.sleep(10)
            return "never"

        # Add completed and running jobs
        completed_id = await scheduler.add_job(quick_task)
        await scheduler.wait(completed_id)

        running_id = await scheduler.add_job(slow_task)
        await asyncio.sleep(0.01)  # Let it start

        # Filter by completed
        response = await client.get("/api/v1/jobs?status_filter=completed")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["id"] == str(completed_id)

        # Filter by running
        response = await client.get("/api/v1/jobs?status_filter=running")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["id"] == str(running_id)

        # Cleanup
        await scheduler.cancel(running_id)

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, client: AsyncClient, app: FastAPI):
        """Test GET /api/v1/jobs/{id} returns job record."""
        scheduler = app.state.scheduler

        async def task():
            return "result"

        job_id = await scheduler.add_job(task)
        await scheduler.wait(job_id)

        # Get specific job
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        assert job["id"] == str(job_id)
        assert job["status"] == "completed"
        assert job["submitted_at"] is not None
        assert job["started_at"] is not None
        assert job["finished_at"] is not None

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client: AsyncClient):
        """Test GET /api/v1/jobs/{id} returns 404 for non-existent job."""
        fake_id = ULID()
        response = await client.get(f"/api/v1/jobs/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_get_job_invalid_ulid(self, client: AsyncClient):
        """Test GET /api/v1/jobs/{id} returns 404 for invalid ULID."""
        response = await client.get("/api/v1/jobs/invalid-ulid")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job(self, client: AsyncClient, app: FastAPI):
        """Test DELETE /api/v1/jobs/{id} deletes job."""
        scheduler = app.state.scheduler

        async def task():
            return "result"

        job_id = await scheduler.add_job(task)
        await scheduler.wait(job_id)

        # Delete job
        response = await client.delete(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 204
        assert response.text == ""

        # Verify job is gone
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_running_job_cancels_it(self, client: AsyncClient, app: FastAPI):
        """Test DELETE /api/v1/jobs/{id} cancels running job."""
        scheduler = app.state.scheduler

        async def long_task():
            await asyncio.sleep(10)
            return "never"

        job_id = await scheduler.add_job(long_task)
        await asyncio.sleep(0.01)  # Let it start

        # Delete while running
        response = await client.delete(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 204

        # Verify job is gone
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, client: AsyncClient):
        """Test DELETE /api/v1/jobs/{id} returns 404 for non-existent job."""
        fake_id = ULID()
        response = await client.delete(f"/api/v1/jobs/{fake_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_job_with_artifact_id(self, client: AsyncClient, app: FastAPI):
        """Test job that returns ULID sets artifact_id."""
        scheduler = app.state.scheduler

        artifact_id = ULID()

        async def task():
            return artifact_id

        job_id = await scheduler.add_job(task)
        await scheduler.wait(job_id)

        # Get job record
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        assert job["artifact_id"] == str(artifact_id)

    @pytest.mark.asyncio
    async def test_failed_job_has_error(self, client: AsyncClient, app: FastAPI):
        """Test failed job includes error traceback."""
        scheduler = app.state.scheduler

        async def failing_task():
            raise ValueError("Something went wrong")

        job_id = await scheduler.add_job(failing_task)

        # Wait for failure
        try:
            await scheduler.wait(job_id)
        except ValueError:
            pass

        # Get job record
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        assert job["status"] == "failed"
        assert job["error"] is not None
        assert "ValueError" in job["error"]
        assert "Something went wrong" in job["error"]

    @pytest.mark.asyncio
    async def test_jobs_sorted_newest_first(self, client: AsyncClient, app: FastAPI):
        """Test GET /api/v1/jobs returns jobs sorted newest first."""
        scheduler = app.state.scheduler

        async def task():
            return "done"

        job_ids = []
        for _ in range(3):
            jid = await scheduler.add_job(task)
            job_ids.append(jid)
            await asyncio.sleep(0.01)  # Ensure different timestamps

        # Get jobs
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 3

        # Should be newest first
        assert jobs[0]["id"] == str(job_ids[2])
        assert jobs[1]["id"] == str(job_ids[1])
        assert jobs[2]["id"] == str(job_ids[0])

    @pytest.mark.asyncio
    async def test_stream_job_status_quick_job(self, client: AsyncClient, app: FastAPI):
        """Test SSE streaming for quick job that completes immediately."""
        scheduler = app.state.scheduler

        async def quick_task():
            return "done"

        job_id = await scheduler.add_job(quick_task)
        await scheduler.wait(job_id)

        # Stream SSE events
        events = []
        async with client.stream("GET", f"/api/v1/jobs/{job_id}/$stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    data = json.loads(line[6:])
                    events.append(data)

        # Should have at least one event with completed status
        assert len(events) >= 1
        assert events[-1]["status"] == "completed"
        assert events[-1]["id"] == str(job_id)

    @pytest.mark.asyncio
    async def test_stream_job_status_running_job(self, client: AsyncClient, app: FastAPI):
        """Test SSE streaming for running job with status transitions."""
        scheduler = app.state.scheduler

        async def slow_task():
            await asyncio.sleep(0.5)
            return "done"

        job_id = await scheduler.add_job(slow_task)

        # Stream SSE events
        events = []
        async with client.stream("GET", f"/api/v1/jobs/{job_id}/$stream?poll_interval=0.1") as response:
            assert response.status_code == 200

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    data = json.loads(line[6:])
                    events.append(data)
                    if data["status"] == "completed":
                        break

        # Should have multiple events showing status transitions
        assert len(events) >= 2
        statuses = [e["status"] for e in events]
        assert "running" in statuses or "pending" in statuses
        assert events[-1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_stream_job_status_failed_job(self, client: AsyncClient, app: FastAPI):
        """Test SSE streaming for failed job."""
        scheduler = app.state.scheduler

        async def failing_task():
            raise ValueError("Task failed")

        job_id = await scheduler.add_job(failing_task)

        # Stream SSE events
        events = []
        async with client.stream("GET", f"/api/v1/jobs/{job_id}/$stream") as response:
            assert response.status_code == 200

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    data = json.loads(line[6:])
                    events.append(data)
                    if data["status"] == "failed":
                        break

        # Final event should show failed status with error
        assert events[-1]["status"] == "failed"
        assert events[-1]["error"] is not None
        assert "ValueError" in events[-1]["error"]

    @pytest.mark.asyncio
    async def test_stream_job_status_not_found(self, client: AsyncClient):
        """Test SSE streaming for non-existent job returns 404."""
        fake_id = ULID()
        response = await client.get(f"/api/v1/jobs/{fake_id}/$stream")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_job_status_invalid_ulid(self, client: AsyncClient):
        """Test SSE streaming with invalid ULID returns 400."""
        response = await client.get("/api/v1/jobs/invalid-ulid/$stream")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid job ID format"

    @pytest.mark.asyncio
    async def test_stream_job_status_custom_poll_interval(self, client: AsyncClient, app: FastAPI):
        """Test SSE streaming with custom poll interval."""
        scheduler = app.state.scheduler

        async def slow_task():
            await asyncio.sleep(0.5)
            return "done"

        job_id = await scheduler.add_job(slow_task)

        # Stream with custom poll interval
        events = []
        async with client.stream("GET", f"/api/v1/jobs/{job_id}/$stream?poll_interval=0.2") as response:
            assert response.status_code == 200

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    data = json.loads(line[6:])
                    events.append(data)
                    if data["status"] == "completed":
                        break

        # Should have received events and completed
        assert len(events) >= 1
        assert events[-1]["status"] == "completed"


class TestJobRouterIntegration:
    """Integration tests for job router with ServiceBuilder."""

    @pytest.mark.asyncio
    async def test_service_builder_with_jobs(self) -> None:
        """Test ServiceBuilder.with_jobs() creates functional job endpoints."""
        info = ServiceInfo(display_name="Test Service")
        app = ServiceBuilder(info=info).with_jobs(prefix="/jobs", tags=["background"]).build()

        # Trigger lifespan to initialize scheduler
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
            ) as client:
                # Check jobs endpoint exists
                response = await client.get("/jobs")
                assert response.status_code == 200
                assert response.json() == []

    @pytest.mark.asyncio
    async def test_service_builder_with_max_concurrency(self) -> None:
        """Test ServiceBuilder.with_jobs(max_concurrency=N) configures scheduler."""
        info = ServiceInfo(display_name="Test Service")
        app = ServiceBuilder(info=info).with_jobs(max_concurrency=2).build()

        # Trigger lifespan to initialize scheduler
        async with app.router.lifespan_context(app):
            # Access scheduler via app.state
            scheduler = app.state.scheduler
            assert scheduler.max_concurrency == 2

    @pytest.mark.asyncio
    async def test_job_endpoints_in_openapi_schema(self) -> None:
        """Test job endpoints appear in OpenAPI schema."""
        info = ServiceInfo(display_name="Test Service")
        app = ServiceBuilder(info=info).with_jobs().build()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            response = await client.get("/openapi.json")
            assert response.status_code == 200
            schema = response.json()

            # Check job endpoints exist in schema
            paths = schema["paths"]
            assert "/api/v1/jobs" in paths
            assert "/api/v1/jobs/{job_id}" in paths

            # Check tags at operation level
            jobs_list_tags = paths["/api/v1/jobs"]["get"]["tags"]
            assert "jobs" in jobs_list_tags
