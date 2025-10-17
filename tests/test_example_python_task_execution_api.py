"""Tests for python_task_execution_api example with Python function execution.

This example demonstrates Python task execution via TaskRegistry:
- Register Python functions using @TaskRegistry.register()
- Tasks can be Python functions (not just shell commands)
- Execution supports both sync and async functions
- Results captured in artifacts with result/error structure
- Handles exceptions gracefully in artifacts
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from examples.python_task_execution_api import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient for testing with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def wait_for_job_completion(client: TestClient, job_id: str, timeout: float = 5.0) -> dict[Any, Any]:
    """Poll job status until completion or timeout."""
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
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_list_python_tasks(client: TestClient) -> None:
    """Test listing tasks shows seeded Python tasks."""
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()

    # Should have at least 5 seeded tasks
    assert isinstance(data, list)
    assert len(data) >= 5

    # Check for Python tasks
    python_tasks = [task for task in data if task["task_type"] == "python"]
    assert len(python_tasks) >= 4

    # Check for specific Python task names
    commands = [task["command"] for task in python_tasks]
    assert "calculate_sum" in commands
    assert "process_data" in commands
    assert "failing_task" in commands


def test_create_python_task(client: TestClient) -> None:
    """Test creating a Python task with parameters."""
    new_task = {
        "command": "calculate_sum",
        "task_type": "python",
        "parameters": {"a": 5, "b": 10},
    }

    response = client.post("/api/v1/tasks", json=new_task)
    assert response.status_code == 201
    created = response.json()

    assert "id" in created
    assert created["command"] == "calculate_sum"
    assert created["task_type"] == "python"
    assert created["parameters"] == {"a": 5, "b": 10}


def test_execute_async_python_task(client: TestClient) -> None:
    """Test executing an async Python function and retrieving results."""
    # Create a Python task
    new_task = {
        "command": "calculate_sum",
        "task_type": "python",
        "parameters": {"a": 15, "b": 27},
    }
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute the task
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    assert execute_response.status_code == 202
    execute_data = execute_response.json()
    job_id = execute_data["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] == "completed"
    assert job["artifact_id"] is not None

    # Get artifact with results
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    assert artifact_response.status_code == 200
    artifact = artifact_response.json()

    # Check artifact structure for Python tasks
    data = artifact["data"]
    assert "task" in data
    assert "result" in data
    assert "error" in data

    # Verify task snapshot
    assert data["task"]["command"] == "calculate_sum"
    assert data["task"]["task_type"] == "python"
    assert data["task"]["parameters"] == {"a": 15, "b": 27}

    # Verify result
    assert data["error"] is None
    assert data["result"] is not None
    assert data["result"]["result"] == 42  # 15 + 27
    assert data["result"]["operation"] == "sum"


def test_execute_sync_python_task(client: TestClient) -> None:
    """Test executing a sync Python function."""
    # Create a task
    new_task = {
        "command": "process_data",
        "task_type": "python",
        "parameters": {"input_text": "Test String", "uppercase": True},
    }
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] == "completed"

    # Get artifact
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    # Verify result
    assert data["error"] is None
    assert data["result"]["original"] == "Test String"
    assert data["result"]["processed"] == "TEST STRING"
    assert data["result"]["length"] == 11


def test_execute_python_task_with_error(client: TestClient) -> None:
    """Test that Python task exceptions are captured in artifacts."""
    # Create a failing task
    new_task = {
        "command": "failing_task",
        "task_type": "python",
        "parameters": {"should_fail": True},
    }
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    # Job completes even if Python function raised exception
    assert job["status"] == "completed"

    # Get artifact
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    # Verify error was captured
    assert data["result"] is None
    assert data["error"] is not None
    assert data["error"]["type"] == "ValueError"
    assert "designed to fail" in data["error"]["message"]
    assert "traceback" in data["error"]


def test_execute_seeded_python_tasks(client: TestClient) -> None:
    """Test executing pre-seeded Python tasks."""
    # Get list of tasks
    response = client.get("/api/v1/tasks")
    tasks = response.json()

    # Find a seeded Python task
    python_tasks = [t for t in tasks if t["task_type"] == "python"]
    assert len(python_tasks) > 0

    # Execute one
    task = python_tasks[0]
    execute_response = client.post(f"/api/v1/tasks/{task['id']}/$execute")
    assert execute_response.status_code == 202
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id)
    assert job["status"] in ["completed", "failed"]


def test_python_task_without_parameters(client: TestClient) -> None:
    """Test Python task can be executed without parameters."""
    # Create a task without parameters
    new_task = {
        "command": "slow_computation",
        "task_type": "python",
        # No parameters field
    }
    create_response = client.post("/api/v1/tasks", json=new_task)
    task = create_response.json()
    task_id = task["id"]

    # Execute
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Wait for completion
    job = wait_for_job_completion(client, job_id, timeout=5.0)
    assert job["status"] == "completed"

    # Get artifact
    artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
    artifact = artifact_response.json()
    data = artifact["data"]

    # Should use default parameters
    assert data["error"] is None
    assert data["result"]["completed"] is True


def test_mixed_shell_and_python_tasks(client: TestClient) -> None:
    """Test that shell and Python tasks can coexist."""
    # Create a shell task
    shell_task = {"command": "echo 'shell task'", "task_type": "shell"}
    shell_response = client.post("/api/v1/tasks", json=shell_task)
    shell_task_data = shell_response.json()

    # Create a Python task
    python_task = {
        "command": "calculate_sum",
        "task_type": "python",
        "parameters": {"a": 1, "b": 1},
    }
    python_response = client.post("/api/v1/tasks", json=python_task)
    python_task_data = python_response.json()

    # Execute both
    shell_exec = client.post(f"/api/v1/tasks/{shell_task_data['id']}/$execute")
    python_exec = client.post(f"/api/v1/tasks/{python_task_data['id']}/$execute")

    shell_job = wait_for_job_completion(client, shell_exec.json()["job_id"])
    python_job = wait_for_job_completion(client, python_exec.json()["job_id"])

    # Both should complete
    assert shell_job["status"] == "completed"
    assert python_job["status"] == "completed"

    # Verify different artifact structures
    shell_artifact = client.get(f"/api/v1/artifacts/{shell_job['artifact_id']}").json()
    python_artifact = client.get(f"/api/v1/artifacts/{python_job['artifact_id']}").json()

    # Shell artifact has stdout/stderr/exit_code
    assert "stdout" in shell_artifact["data"]
    assert "stderr" in shell_artifact["data"]
    assert "exit_code" in shell_artifact["data"]

    # Python artifact has result/error
    assert "result" in python_artifact["data"]
    assert "error" in python_artifact["data"]
    assert python_artifact["data"]["result"]["result"] == 2
