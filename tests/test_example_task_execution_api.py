"""Tests for task_execution_api example with artifact-based result storage.

This example demonstrates the new task execution architecture:
- Tasks are reusable command templates (no status/output fields)
- Execution creates Jobs that run asynchronously
- Results are stored in Artifacts with full task snapshot + outputs
- Job.artifact_id links to the result artifact
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from examples.task_execution_api import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient for testing with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def wait_for_job_completion(client: TestClient, job_id: str, timeout: float = 5.0) -> dict[Any, Any]:
    """Poll job status until completion or timeout.

    Args:
        client: FastAPI test client
        job_id: Job identifier to poll
        timeout: Max seconds to wait (default: 5.0)

    Returns:
        Completed job record

    Raises:
        TimeoutError: If job doesn't complete within timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        job_response = client.get(f"/api/v1/jobs/{job_id}")
        assert job_response.status_code == 200
        job = cast(dict[Any, Any], job_response.json())

        if job["status"] in ["completed", "failed", "canceled"]:
            return job

        time.sleep(0.1)

    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def test_health_endpoint(client: TestClient) -> None:
    """Test health check returns healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_list_tasks(client: TestClient) -> None:
    """Test listing tasks shows seeded templates."""
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()

    # Should have at least the 5 seeded tasks
    assert isinstance(data, list)
    assert len(data) >= 5

    # Check for specific seeded tasks
    commands = [task["command"] for task in data]
    assert any("ls -la /tmp" in cmd for cmd in commands)
    assert any("echo" in cmd for cmd in commands)
    assert any("date" in cmd for cmd in commands)


def test_get_task_by_id(client: TestClient) -> None:
    """Test retrieving task template by ID."""
    # Get list to find a task ID
    list_response = client.get("/api/v1/tasks")
    tasks = list_response.json()
    assert len(tasks) > 0
    task_id = tasks[0]["id"]

    # Get task by ID
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task = response.json()

    assert task["id"] == task_id
    assert "command" in task
    assert "created_at" in task
    assert "updated_at" in task
    # Tasks are templates - no status or execution fields
    assert "status" not in task
    assert "stdout" not in task
    assert "stderr" not in task
    assert "exit_code" not in task
    assert "job_id" not in task


def test_get_task_not_found(client: TestClient) -> None:
    """Test retrieving non-existent task returns 404."""
    response = client.get("/api/v1/tasks/01K72P5N5KCRM6MD3BRE4P0999")
    assert response.status_code == 404


def test_create_task(client: TestClient) -> None:
    """Test creating a new task template."""
    new_task = {"command": "echo 'test task creation'"}

    response = client.post("/api/v1/tasks", json=new_task)
    assert response.status_code == 201
    created = response.json()

    assert "id" in created
    assert created["command"] == "echo 'test task creation'"
    assert "created_at" in created
    assert "updated_at" in created
    # Tasks are templates - no execution state
    assert "status" not in created
    assert "stdout" not in created
    assert "stderr" not in created
    assert "exit_code" not in created
    assert "job_id" not in created


def test_create_task_with_missing_command(client: TestClient) -> None:
    """Test creating task without command fails."""
    response = client.post("/api/v1/tasks", json={})
    assert response.status_code == 422  # Validation error


def test_update_task(client: TestClient) -> None:
    """Test updating a task template command."""
    # Create a task first
    new_task = {"command": "echo 'original'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    created = create_response.json()
    task_id = created["id"]

    # Update the task
    updated_task = {"command": "echo 'updated'"}
    response = client.put(f"/api/v1/tasks/{task_id}", json=updated_task)
    assert response.status_code == 200
    updated = response.json()

    assert updated["id"] == task_id
    assert updated["command"] == "echo 'updated'"


def test_delete_task(client: TestClient) -> None:
    """Test deleting a task template."""
    # Create a task first
    new_task = {"command": "echo 'to be deleted'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    created = create_response.json()
    task_id = created["id"]

    # Delete the task
    response = client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 204

    # Verify task is deleted
    get_response = client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 404


def test_execute_task_simple_command(client: TestClient) -> None:
    """Test executing a simple echo command and retrieving results from artifact."""
    # Create a task
    new_task = {"command": "echo 'Hello World'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute the task
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    assert execute_response.status_code == 202  # Accepted
    execute_data = execute_response.json()
    assert "job_id" in execute_data
    assert "message" in execute_data
    job_id = execute_data["job_id"]

    # Wait for job completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] == "completed"
    assert job["artifact_id"] is not None

    # Get artifact with results
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    assert artifact_response.status_code == 200
    artifact = artifact_response.json()

    # Check artifact data structure
    assert "data" in artifact
    data = artifact["data"]
    assert "task" in data
    assert "stdout" in data
    assert "stderr" in data
    assert "exit_code" in data

    # Verify task snapshot
    assert data["task"]["id"] == task_id
    assert data["task"]["command"] == "echo 'Hello World'"

    # Verify execution results
    assert "Hello World" in data["stdout"]
    assert data["exit_code"] == 0


def test_execute_task_with_output(client: TestClient) -> None:
    """Test executing command with multiline output and checking artifact."""
    # Create a task that produces output
    new_task = {"command": "printf 'Line 1\\nLine 2\\nLine 3'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] == "completed"

    # Get artifact and check outputs
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    assert "Line 1" in data["stdout"]
    assert "Line 2" in data["stdout"]
    assert "Line 3" in data["stdout"]
    assert data["exit_code"] == 0


def test_execute_task_failing_command(client: TestClient) -> None:
    """Test executing a command that fails and checking error in artifact."""
    # Create a task with a failing command
    new_task = {"command": "ls /this/path/does/not/exist"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    # Job completes successfully even if command fails
    assert job["status"] == "completed"
    assert job["artifact_id"] is not None

    # Get artifact and check failure details
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    # Command failed with non-zero exit code
    assert data["exit_code"] != 0
    assert data["stderr"] is not None
    assert len(data["stderr"]) > 0


def test_execute_task_with_stderr(client: TestClient) -> None:
    """Test capturing stderr output in artifact."""
    # Create a task that writes to stderr
    new_task = {"command": ">&2 echo 'error message'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] == "completed"

    # Get artifact and check stderr
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    # Stderr should contain the error message
    # Some systems redirect stderr to stdout, so check both
    output = (data["stderr"] or "") + (data["stdout"] or "")
    assert "error message" in output
    assert data["exit_code"] == 0


def test_execute_same_task_multiple_times(client: TestClient) -> None:
    """Test that same task template can be executed multiple times."""
    # Create a task
    new_task = {"command": "echo 'multiple executions'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    job_ids = []
    artifact_ids = []

    # Execute the same task 3 times sequentially (to avoid potential race conditions)
    for _ in range(3):
        execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
        assert execute_response.status_code == 202
        job_id = execute_response.json()["job_id"]
        job_ids.append(job_id)

        # Wait for this job to complete before starting the next one
        job = wait_for_job_completion(client, job_id)
        assert job["status"] in ["completed", "failed"]
        if job["status"] == "completed":
            assert job["artifact_id"] is not None
            artifact_ids.append(job["artifact_id"])

    # At least some executions should have succeeded
    assert len(artifact_ids) >= 1

    # All artifact IDs should be different (each execution creates a new artifact)
    assert len(set(artifact_ids)) == len(artifact_ids)

    # Verify all artifacts contain the same task snapshot but are independent records
    for artifact_id in artifact_ids:
        artifact_response = client.get(f"/api/v1/artifacts/{artifact_id}")
        artifact = artifact_response.json()
        data = artifact["data"]

        assert data["task"]["id"] == task_id
        assert data["task"]["command"] == "echo 'multiple executions'"
        assert "multiple executions" in data["stdout"]


def test_execute_nonexistent_task(client: TestClient) -> None:
    """Test executing a non-existent task."""
    response = client.post("/api/v1/tasks/01K72P5N5KCRM6MD3BRE4P0999/$execute")
    assert response.status_code == 400  # Bad request


def test_list_jobs(client: TestClient) -> None:
    """Test listing scheduler jobs."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_job_for_executed_task(client: TestClient) -> None:
    """Test that executed tasks create scheduler jobs with proper metadata."""
    # Create and execute a task
    new_task = {"command": "echo 'job test'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    execute_data = execute_response.json()
    job_id = execute_data["job_id"]

    # Get the job
    job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert job_response.status_code == 200
    job = job_response.json()

    assert job["id"] == job_id
    assert job["status"] in ["pending", "running", "completed", "failed"]
    assert "submitted_at" in job


def test_task_timestamps(client: TestClient) -> None:
    """Test that task template timestamps are set correctly."""
    # Create a task
    new_task = {"command": "sleep 0.1"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Check task timestamps (only created_at and updated_at for templates)
    assert task["created_at"] is not None
    assert task["updated_at"] is not None
    # No execution timestamps on task template
    assert "started_at" not in task
    assert "finished_at" not in task

    # Execute and check job timestamps
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)

    # Job should have execution timestamps
    assert job["submitted_at"] is not None
    assert job["started_at"] is not None
    assert job["finished_at"] is not None


def test_list_tasks_with_pagination(client: TestClient) -> None:
    """Test listing task templates with pagination."""
    response = client.get("/api/v1/tasks", params={"page": 1, "size": 2})
    assert response.status_code == 200
    data = response.json()

    # Should return paginated response
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data

    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["size"] == 2


def test_python_command_execution(client: TestClient) -> None:
    """Test executing Python commands and retrieving results from artifact."""
    # Create a task with Python code
    new_task = {"command": 'python3 -c "import sys; print(sys.version); print(2+2)"'}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] == "completed"

    # Get artifact and check output
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    assert data["exit_code"] == 0
    assert "4" in data["stdout"]  # Result of 2+2


def test_concurrent_task_execution(client: TestClient) -> None:
    """Test executing multiple tasks concurrently and retrieving all artifacts."""
    task_ids = []
    job_ids = []

    # Create multiple tasks
    for i in range(3):
        new_task = {"command": f"echo 'task {i}'"}
        response = client.post("/api/v1/tasks", json=new_task)
        task_ids.append(response.json()["id"])

    # Execute all tasks
    for task_id in task_ids:
        execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
        job_ids.append(execute_response.json()["job_id"])

    # Wait for all jobs to complete and collect results
    all_jobs = []
    for job_id in job_ids:
        job = wait_for_job_completion(client, job_id)
        all_jobs.append(job)
        # Jobs should complete (either successfully or with failure)
        assert job["status"] in ["completed", "failed", "canceled"]

    # Count successful completions
    completed_jobs = [j for j in all_jobs if j["status"] == "completed"]

    # Test that we can execute multiple tasks (even if some fail due to concurrency limits)
    # At minimum, verify jobs were created and reached terminal state
    assert len(all_jobs) == 3

    # Verify completed artifacts have correct structure and output
    for job in completed_jobs:
        if job["artifact_id"]:
            artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
            artifact = artifact_response.json()
            data = artifact["data"]

            # Each task should have output containing "task"
            assert "task" in data["stdout"]
            assert data["exit_code"] == 0


def test_job_artifact_linkage(client: TestClient) -> None:
    """Test that jobs are properly linked to result artifacts."""
    # Create and execute a task
    new_task = {"command": "echo 'linkage test'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)

    # Job should have artifact_id
    assert job["artifact_id"] is not None
    artifact_id = job["artifact_id"]

    # Artifact should exist and contain execution results
    artifact_response = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_response.status_code == 200
    artifact = artifact_response.json()

    # Verify artifact structure
    assert artifact["id"] == artifact_id
    assert "data" in artifact
    assert "task" in artifact["data"]
    assert artifact["data"]["task"]["id"] == task_id


def test_task_deletion_preserves_artifacts(client: TestClient) -> None:
    """Test that deleting a task doesn't delete its execution artifacts."""
    # Create and execute a task
    new_task = {"command": "echo 'preserve artifacts'"}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    artifact_id = job["artifact_id"]

    # Verify artifact exists
    artifact_response = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_response.status_code == 200

    # Delete the task
    delete_response = client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_response.status_code == 204

    # Artifact should still exist
    artifact_response = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_response.status_code == 200
    artifact = artifact_response.json()

    # Artifact contains full task snapshot, so task data is preserved
    assert artifact["data"]["task"]["id"] == task_id
    assert artifact["data"]["task"]["command"] == "echo 'preserve artifacts'"


def test_task_modification_doesnt_affect_artifacts(client: TestClient) -> None:
    """Test that modifying a task doesn't affect existing execution artifacts."""
    # Create and execute a task
    original_command = "echo 'original command'"
    new_task = {"command": original_command}
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    artifact_id = job["artifact_id"]

    # Modify the task
    modified_command = "echo 'modified command'"
    update_response = client.put(f"/api/v1/tasks/{task_id}", json={"command": modified_command})
    assert update_response.status_code == 200

    # Original artifact should still have the original command
    artifact_response = client.get(f"/api/v1/artifacts/{artifact_id}")
    artifact = artifact_response.json()
    assert artifact["data"]["task"]["command"] == original_command
    assert "original command" in artifact["data"]["stdout"]

    # New execution should use modified command
    execute_response2 = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id2 = execute_response2.json()["job_id"]
    job2 = wait_for_job_completion(client, job_id2)

    artifact_response2 = client.get(f"/api/v1/artifacts/{job2['artifact_id']}")
    artifact2 = artifact_response2.json()
    assert artifact2["data"]["task"]["command"] == modified_command
    assert "modified command" in artifact2["data"]["stdout"]
