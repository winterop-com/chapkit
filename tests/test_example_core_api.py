"""Tests for core_api example using TestClient.

Tests use FastAPI's TestClient instead of running a separate server.
Validates BaseServiceBuilder functionality with custom User entity.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from examples.core_api import app


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
    assert "checks" in data
    assert "database" in data["checks"]
    assert data["checks"]["database"]["state"] == "healthy"


def test_system_endpoint(client: TestClient) -> None:
    """Test system info endpoint returns system metadata."""
    response = client.get("/api/v1/system")
    assert response.status_code == 200
    data = response.json()
    assert "python_version" in data
    assert "platform" in data
    assert "current_time" in data
    assert "timezone" in data
    assert "hostname" in data


def test_info_endpoint(client: TestClient) -> None:
    """Test service info endpoint returns service metadata."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Core User Service"
    assert data["version"] == "1.0.0"
    assert data["summary"] == "User management API using core-only features"


def test_create_user(client: TestClient) -> None:
    """Test creating a new user."""
    new_user = {
        "username": "johndoe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "is_active": True,
    }

    response = client.post("/api/v1/users", json=new_user)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["username"] == "johndoe"
    assert data["email"] == "john@example.com"
    assert data["full_name"] == "John Doe"
    assert data["is_active"] is True

    # Verify Location header
    assert "Location" in response.headers
    assert f"/api/v1/users/{data['id']}" in response.headers["Location"]


def test_list_users(client: TestClient) -> None:
    """Test listing all users."""
    # Create a few users first
    users_to_create = [
        {"username": "alice", "email": "alice@example.com", "full_name": "Alice Smith"},
        {"username": "bob", "email": "bob@example.com", "full_name": "Bob Jones"},
    ]

    for user in users_to_create:
        client.post("/api/v1/users", json=user)

    # List all users
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()

    # Should be a list
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verify structure
    for user in data:
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "created_at" in user
        assert "updated_at" in user


def test_list_users_with_pagination(client: TestClient) -> None:
    """Test listing users with pagination."""
    # Create multiple users to test pagination
    for i in range(5):
        client.post(
            "/api/v1/users",
            json={
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "full_name": f"User {i}",
            },
        )

    response = client.get("/api/v1/users", params={"page": 1, "size": 3})
    assert response.status_code == 200
    data = response.json()

    # Should return paginated response
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data

    assert len(data["items"]) <= 3
    assert data["page"] == 1
    assert data["size"] == 3
    assert data["total"] >= 5


def test_get_user_by_id(client: TestClient) -> None:
    """Test retrieving user by ID."""
    # Create a user first
    new_user = {"username": "testuser", "email": "test@example.com", "full_name": "Test User"}
    create_response = client.post("/api/v1/users", json=new_user)
    created = create_response.json()
    user_id = created["id"]

    # Get by ID
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == user_id
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_get_user_by_invalid_ulid(client: TestClient) -> None:
    """Test retrieving user with invalid ULID format returns 400."""
    response = client.get("/api/v1/users/not-a-valid-ulid")
    assert response.status_code == 400
    data = response.json()
    assert "invalid ulid" in data["detail"].lower()


def test_get_user_by_id_not_found(client: TestClient) -> None:
    """Test retrieving non-existent user by ID returns 404."""
    # Use a valid ULID format but non-existent ID
    response = client.get("/api/v1/users/01K72P5N5KCRM6MD3BRE4P0999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_update_user(client: TestClient) -> None:
    """Test updating an existing user."""
    # Create a user first
    new_user = {"username": "updateuser", "email": "update@example.com", "full_name": "Update User"}
    create_response = client.post("/api/v1/users", json=new_user)
    created = create_response.json()
    user_id = created["id"]

    # Update it
    updated_user = {
        "id": user_id,
        "username": "updateuser",
        "email": "updated@example.com",  # Changed
        "full_name": "Updated User Name",  # Changed
        "is_active": False,  # Changed
    }

    response = client.put(f"/api/v1/users/{user_id}", json=updated_user)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == user_id
    assert data["username"] == "updateuser"
    assert data["email"] == "updated@example.com"
    assert data["full_name"] == "Updated User Name"
    assert data["is_active"] is False


def test_update_user_not_found(client: TestClient) -> None:
    """Test updating non-existent user returns 404."""
    user_id = "01K72P5N5KCRM6MD3BRE4P0999"
    updated_user = {
        "id": user_id,
        "username": "ghost",
        "email": "ghost@example.com",
    }

    response = client.put(f"/api/v1/users/{user_id}", json=updated_user)
    assert response.status_code == 404


def test_delete_user(client: TestClient) -> None:
    """Test deleting a user."""
    # Create a user first
    new_user = {"username": "deleteuser", "email": "delete@example.com"}
    create_response = client.post("/api/v1/users", json=new_user)
    created = create_response.json()
    user_id = created["id"]

    # Delete it
    response = client.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 404


def test_delete_user_not_found(client: TestClient) -> None:
    """Test deleting non-existent user returns 404."""
    response = client.delete("/api/v1/users/01K72P5N5KCRM6MD3BRE4P0999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_jobs_endpoint_exists(client: TestClient) -> None:
    """Test that job scheduler endpoints are available."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    # Should return empty list initially
    assert isinstance(data, list)


def test_openapi_schema(client: TestClient) -> None:
    """Test OpenAPI schema is generated correctly."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    assert schema["info"]["title"] == "Core User Service"
    assert schema["info"]["version"] == "1.0.0"
    assert "paths" in schema
    assert "/api/v1/users" in schema["paths"]
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/system" in schema["paths"]
