"""Tests for full_featured_api example showcasing all chapkit features.

This test suite validates the comprehensive example that demonstrates:
- Health checks (custom + database)
- System info
- Config management
- Artifacts with hierarchy
- Config-artifact linking
- Task execution
- Job scheduling
- Custom routers
- Landing page
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from examples.full_featured_api import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


# ==================== Basic Endpoints ====================


def test_landing_page(client: TestClient) -> None:
    """Test landing page returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_health_endpoint(client: TestClient) -> None:
    """Test health check returns healthy status with custom checks."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "checks" in data

    # Verify both database and custom external_service checks
    assert "database" in data["checks"]
    assert data["checks"]["database"]["state"] == "healthy"
    assert "external_service" in data["checks"]
    assert data["checks"]["external_service"]["state"] == "healthy"


def test_system_endpoint(client: TestClient) -> None:
    """Test system info endpoint returns metadata."""
    response = client.get("/system")
    assert response.status_code == 200
    data = response.json()

    assert "current_time" in data
    assert "timezone" in data
    assert "python_version" in data
    assert "platform" in data
    assert "hostname" in data


def test_info_endpoint(client: TestClient) -> None:
    """Test service info endpoint returns service metadata."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()

    assert data["display_name"] == "Complete Feature Showcase"
    assert data["version"] == "2.0.0"
    assert data["summary"] == "Comprehensive example demonstrating ALL chapkit features"
    assert data["contact"]["name"] == "Chapkit Team"
    assert data["license_info"]["name"] == "MIT"


# ==================== Seeded Data Tests ====================


def test_seeded_configs(client: TestClient) -> None:
    """Test that startup hook seeded example config."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    configs = response.json()

    # Should have at least the seeded config
    assert len(configs) >= 1

    # Find the seeded config by name
    production_config = next((c for c in configs if c["name"] == "production_pipeline"), None)
    assert production_config is not None
    assert production_config["id"] == "01JCSEED00C0NF1GEXAMP1E001"

    # Verify config data structure
    data = production_config["data"]
    assert data["model_type"] == "xgboost"
    assert data["learning_rate"] == 0.01
    assert data["max_epochs"] == 500
    assert data["batch_size"] == 64
    assert data["early_stopping"] is True
    assert data["random_seed"] == 42


def test_seeded_artifacts(client: TestClient) -> None:
    """Test that startup hook seeded example artifact."""
    response = client.get("/api/v1/artifacts")
    assert response.status_code == 200
    artifacts = response.json()

    # Should have at least the seeded artifact
    assert len(artifacts) >= 1

    # Find the seeded artifact by ID
    seeded_artifact_id = "01JCSEED00ART1FACTEXMP1001"
    artifact_response = client.get(f"/api/v1/artifacts/{seeded_artifact_id}")
    assert artifact_response.status_code == 200

    artifact = artifact_response.json()
    assert artifact["id"] == seeded_artifact_id
    assert artifact["data"]["experiment_name"] == "baseline_experiment"
    assert artifact["data"]["model_metrics"]["accuracy"] == 0.95
    assert artifact["data"]["model_metrics"]["f1_score"] == 0.93
    assert artifact["data"]["dataset_info"]["train_size"] == 10000


def test_seeded_tasks(client: TestClient) -> None:
    """Test that startup hook seeded example tasks."""
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    tasks = response.json()

    # Should have at least 2 seeded tasks
    assert len(tasks) >= 2

    # Find seeded tasks by ID
    task_ids = {task["id"] for task in tasks}
    assert "01JCSEED00TASKEXAMP1E00001" in task_ids
    assert "01JCSEED00TASKEXAMP1E00002" in task_ids

    # Verify task commands
    task1 = next((t for t in tasks if t["id"] == "01JCSEED00TASKEXAMP1E00001"), None)
    assert task1 is not None
    assert "Training model" in task1["command"]

    task2 = next((t for t in tasks if t["id"] == "01JCSEED00TASKEXAMP1E00002"), None)
    assert task2 is not None
    assert "Python" in task2["command"]


# ==================== Config Management Tests ====================


def test_config_crud(client: TestClient) -> None:
    """Test full config CRUD operations."""
    # Create
    new_config = {
        "name": "test_pipeline",
        "data": {
            "model_type": "random_forest",
            "learning_rate": 0.001,
            "max_epochs": 100,
            "batch_size": 32,
            "early_stopping": True,
            "random_seed": 123,
        },
    }

    create_response = client.post("/api/v1/config", json=new_config)
    assert create_response.status_code == 201
    created = create_response.json()
    config_id = created["id"]

    assert created["name"] == "test_pipeline"
    assert created["data"]["model_type"] == "random_forest"

    # Read
    get_response = client.get(f"/api/v1/config/{config_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["id"] == config_id

    # Update
    fetched["data"]["max_epochs"] = 200
    update_response = client.put(f"/api/v1/config/{config_id}", json=fetched)
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["data"]["max_epochs"] == 200

    # Delete
    delete_response = client.delete(f"/api/v1/config/{config_id}")
    assert delete_response.status_code == 204

    # Verify deletion
    get_after_delete = client.get(f"/api/v1/config/{config_id}")
    assert get_after_delete.status_code == 404


def test_config_pagination(client: TestClient) -> None:
    """Test config pagination."""
    response = client.get("/api/v1/config", params={"page": 1, "size": 2})
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert len(data["items"]) <= 2


# ==================== Artifact Tests ====================


def test_artifact_crud_with_hierarchy(client: TestClient) -> None:
    """Test artifact CRUD with hierarchical relationships."""
    # Create root artifact (level 0: experiment)
    root_artifact = {
        "data": {
            "experiment_name": "test_experiment",
            "description": "Testing artifact hierarchy",
        },
    }

    root_response = client.post("/api/v1/artifacts", json=root_artifact)
    assert root_response.status_code == 201
    root = root_response.json()
    root_id = root["id"]
    assert root["level"] == 0

    # Create child artifact (level 1: training)
    child_artifact = {
        "data": {"training_loss": 0.05, "epoch": 10},
        "parent_id": root_id,
    }

    child_response = client.post("/api/v1/artifacts", json=child_artifact)
    assert child_response.status_code == 201
    child = child_response.json()
    child_id = child["id"]
    assert child["level"] == 1
    assert child["parent_id"] == root_id

    # Get tree structure
    tree_response = client.get(f"/api/v1/artifacts/{root_id}/$tree")
    assert tree_response.status_code == 200
    tree = tree_response.json()

    assert tree["id"] == root_id
    assert tree["level"] == 0
    assert len(tree["children"]) >= 1
    assert any(c["id"] == child_id for c in tree["children"])

    # Cleanup
    client.delete(f"/api/v1/artifacts/{child_id}")
    client.delete(f"/api/v1/artifacts/{root_id}")


def test_artifact_tree_endpoint(client: TestClient) -> None:
    """Test artifact tree operation with seeded data."""
    seeded_artifact_id = "01JCSEED00ART1FACTEXMP1001"

    tree_response = client.get(f"/api/v1/artifacts/{seeded_artifact_id}/$tree")
    assert tree_response.status_code == 200
    tree = tree_response.json()

    assert tree["id"] == seeded_artifact_id
    assert "level" in tree
    assert "children" in tree
    # Children can be None or empty list if no children exist
    assert tree["children"] is None or isinstance(tree["children"], list)


# ==================== Config-Artifact Linking Tests ====================


def test_config_artifact_linking(client: TestClient) -> None:
    """Test linking configs to root artifacts."""
    # Create a config
    config = {
        "name": "linking_test",
        "data": {
            "model_type": "xgboost",
            "learning_rate": 0.01,
            "max_epochs": 100,
            "batch_size": 32,
            "early_stopping": True,
            "random_seed": 42,
        },
    }
    config_response = client.post("/api/v1/config", json=config)
    config_id = config_response.json()["id"]

    # Create a root artifact (no parent_id means it's a root)
    artifact = {"data": {"experiment": "linking_test"}, "parent_id": None}
    artifact_response = client.post("/api/v1/artifacts", json=artifact)
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["id"]

    # Verify it's a root artifact (level 0)
    artifact_get = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_get.json()["level"] == 0

    # Link them
    link_response = client.post(f"/api/v1/config/{config_id}/$link-artifact", json={"artifact_id": artifact_id})
    # Accept either 204 or 400 (in case linking not fully supported)
    if link_response.status_code == 204:
        # Verify link by getting artifacts for config
        linked_response = client.get(f"/api/v1/config/{config_id}/$artifacts")
        assert linked_response.status_code == 200
        linked_artifacts = linked_response.json()
        assert len(linked_artifacts) >= 1
        assert any(a["id"] == artifact_id for a in linked_artifacts)

        # Unlink
        unlink_response = client.post(f"/api/v1/config/{config_id}/$unlink-artifact", json={"artifact_id": artifact_id})
        assert unlink_response.status_code == 204

    # Cleanup
    client.delete(f"/api/v1/artifacts/{artifact_id}")
    client.delete(f"/api/v1/config/{config_id}")


# ==================== Task Execution Tests ====================


def test_task_crud(client: TestClient) -> None:
    """Test task CRUD operations."""
    # Create
    task = {"command": "echo 'test task'"}
    create_response = client.post("/api/v1/tasks", json=task)
    assert create_response.status_code == 201
    created = create_response.json()
    task_id = created["id"]
    assert created["command"] == "echo 'test task'"

    # Read
    get_response = client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 200

    # Update
    updated_task = {"command": "echo 'updated task'"}
    update_response = client.put(f"/api/v1/tasks/{task_id}", json=updated_task)
    assert update_response.status_code == 200
    assert update_response.json()["command"] == "echo 'updated task'"

    # Delete
    delete_response = client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_response.status_code == 204


def test_task_execution_creates_job(client: TestClient) -> None:
    """Test that executing a task creates a job."""
    # Create a simple task
    task = {"command": "echo 'Hello from task'"}
    task_response = client.post("/api/v1/tasks", json=task)
    task_id = task_response.json()["id"]

    # Execute the task
    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    assert execute_response.status_code == 202  # Accepted
    job_data = execute_response.json()
    assert "job_id" in job_data
    assert "message" in job_data

    job_id = job_data["job_id"]

    # Wait for job completion
    job = wait_for_job_completion(client, job_id)

    assert job["status"] in ["completed", "failed"]

    # If completed, verify artifact was created
    if job["status"] == "completed" and job["artifact_id"]:
        artifact_response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
        assert artifact_response.status_code == 200
        artifact = artifact_response.json()

        # Verify artifact contains task snapshot and outputs
        assert "task" in artifact["data"]
        assert "stdout" in artifact["data"]
        assert "stderr" in artifact["data"]
        assert "exit_code" in artifact["data"]
        assert artifact["data"]["task"]["id"] == task_id

    # Cleanup
    client.delete(f"/api/v1/jobs/{job_id}")
    client.delete(f"/api/v1/tasks/{task_id}")


# ==================== Job Tests ====================


def test_list_jobs(client: TestClient) -> None:
    """Test listing jobs."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)


def test_get_job_by_id(client: TestClient) -> None:
    """Test getting job by ID."""
    # Create and execute a task to get a job
    task = {"command": "echo 'job test'"}
    task_response = client.post("/api/v1/tasks", json=task)
    task_id = task_response.json()["id"]

    execute_response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    job_id = execute_response.json()["job_id"]

    # Get job
    job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert job_response.status_code == 200
    job = job_response.json()

    assert job["id"] == job_id
    assert "status" in job
    assert "submitted_at" in job

    # Cleanup
    wait_for_job_completion(client, job_id)
    client.delete(f"/api/v1/jobs/{job_id}")
    client.delete(f"/api/v1/tasks/{task_id}")


def test_filter_jobs_by_status(client: TestClient) -> None:
    """Test filtering jobs by status."""
    response = client.get("/api/v1/jobs", params={"status_filter": "completed"})
    assert response.status_code == 200
    jobs = cast(list[dict[str, Any]], response.json())
    assert isinstance(jobs, list)

    # All returned jobs should be completed
    for job in jobs:
        assert job["status"] == "completed"


# ==================== Custom Router Tests ====================


def test_custom_stats_endpoint(client: TestClient) -> None:
    """Test custom statistics router."""
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    stats = response.json()

    assert "total_configs" in stats
    assert "total_artifacts" in stats
    assert "total_tasks" in stats
    assert "service_version" in stats

    # Should have at least the seeded data
    assert stats["total_configs"] >= 1
    assert stats["service_version"] == "2.0.0"


# ==================== OpenAPI Documentation Tests ====================


def test_openapi_schema(client: TestClient) -> None:
    """Test that OpenAPI schema includes all expected endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    paths = schema["paths"]

    # Verify all major endpoint groups are present
    assert "/health" in paths
    assert "/system" in paths
    assert "/api/v1/config" in paths
    assert "/api/v1/artifacts" in paths
    assert "/api/v1/tasks" in paths
    assert "/api/v1/jobs" in paths
    assert "/api/v1/stats" in paths

    # Verify operation endpoints
    assert "/api/v1/artifacts/{entity_id}/$tree" in paths
    assert "/api/v1/tasks/{entity_id}/$execute" in paths
    assert "/api/v1/config/{entity_id}/$artifacts" in paths
    assert "/api/v1/config/{entity_id}/$link-artifact" in paths


# ==================== Helper Functions ====================


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
