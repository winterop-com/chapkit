"""Tests for TaskRouter error handling."""

from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from ulid import ULID

from chapkit import TaskIn, TaskManager, TaskOut
from chapkit.modules.task import TaskRouter


def test_execute_task_value_error_returns_400() -> None:
    """Test that ValueError from execute_task returns 400 Bad Request."""
    # Create mock manager that raises ValueError
    mock_manager = Mock(spec=TaskManager)
    mock_manager.execute_task = AsyncMock(side_effect=ValueError("Task not found"))

    def manager_factory() -> TaskManager:
        return mock_manager

    # Create app with router
    app = FastAPI()
    router = TaskRouter.create(
        prefix="/api/v1/tasks",
        tags=["tasks"],
        entity_in_type=TaskIn,
        entity_out_type=TaskOut,
        manager_factory=manager_factory,
    )
    app.include_router(router)

    client = TestClient(app)
    task_id = ULID()

    response = client.post(f"/api/v1/tasks/{task_id}/$execute")

    assert response.status_code == 400
    assert "Task not found" in response.json()["detail"]


def test_execute_task_runtime_error_returns_409() -> None:
    """Test that RuntimeError from execute_task returns 409 Conflict."""
    # Create mock manager that raises RuntimeError
    mock_manager = Mock(spec=TaskManager)
    mock_manager.execute_task = AsyncMock(side_effect=RuntimeError("Database instance required for task execution"))

    def manager_factory() -> TaskManager:
        return mock_manager

    # Create app with router
    app = FastAPI()
    router = TaskRouter.create(
        prefix="/api/v1/tasks",
        tags=["tasks"],
        entity_in_type=TaskIn,
        entity_out_type=TaskOut,
        manager_factory=manager_factory,
    )
    app.include_router(router)

    client = TestClient(app)
    task_id = ULID()

    response = client.post(f"/api/v1/tasks/{task_id}/$execute")

    assert response.status_code == 409
    assert "Database instance required" in response.json()["detail"]


def test_execute_task_with_valid_ulid() -> None:
    """Test execute_task endpoint with valid ULID."""
    mock_manager = Mock(spec=TaskManager)
    job_id = ULID()
    mock_manager.execute_task = AsyncMock(return_value=job_id)

    def manager_factory() -> TaskManager:
        return mock_manager

    app = FastAPI()
    router = TaskRouter.create(
        prefix="/api/v1/tasks",
        tags=["tasks"],
        entity_in_type=TaskIn,
        entity_out_type=TaskOut,
        manager_factory=manager_factory,
    )
    app.include_router(router)

    client = TestClient(app)
    task_id = ULID()

    response = client.post(f"/api/v1/tasks/{task_id}/$execute")

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert "submitted for execution" in data["message"]
