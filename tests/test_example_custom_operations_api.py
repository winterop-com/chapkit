"""Tests for custom_operations_api example using TestClient.

This example demonstrates custom operations with various HTTP methods.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from examples.custom_operations_api import app


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


def test_list_configs(client: TestClient) -> None:
    """Test listing all seeded feature configs."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()

    # Should be a list of 3 seeded configs
    assert isinstance(data, list)
    assert len(data) == 3

    # Check config names
    names = {config["name"] for config in data}
    assert names == {"api_rate_limiting", "cache_optimization", "experimental_features"}

    # Verify structure
    for config in data:
        assert "id" in config
        assert "name" in config
        assert "data" in config
        assert "enabled" in config["data"]
        assert "max_requests" in config["data"]
        assert "timeout_seconds" in config["data"]
        assert "tags" in config["data"]


def test_get_config_by_id(client: TestClient) -> None:
    """Test retrieving config by ID."""
    # Get the list to obtain a valid ID
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    config_id = configs[0]["id"]

    response = client.get(f"/api/v1/config/{config_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == config_id
    assert "name" in data
    assert "data" in data


def test_enable_operation(client: TestClient) -> None:
    """Test PATCH operation to toggle enabled flag."""
    # Get experimental_features config (initially disabled)
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    experimental = next((c for c in configs if c["name"] == "experimental_features"), None)
    assert experimental is not None
    config_id = experimental["id"]
    initial_enabled = experimental["data"]["enabled"]

    # Toggle enabled flag
    response = client.patch(f"/api/v1/config/{config_id}/$enable", params={"enabled": not initial_enabled})
    assert response.status_code == 200
    updated = response.json()

    assert updated["id"] == config_id
    assert updated["data"]["enabled"] is not initial_enabled

    # Toggle back
    response2 = client.patch(f"/api/v1/config/{config_id}/$enable", params={"enabled": initial_enabled})
    assert response2.status_code == 200
    restored = response2.json()
    assert restored["data"]["enabled"] is initial_enabled


def test_validate_operation(client: TestClient) -> None:
    """Test GET operation to validate configuration."""
    # Get a valid config
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    config_id = configs[0]["id"]

    response = client.get(f"/api/v1/config/{config_id}/$validate")
    assert response.status_code == 200
    validation = response.json()

    # Verify validation result structure
    assert "valid" in validation
    assert "errors" in validation
    assert "warnings" in validation
    assert isinstance(validation["errors"], list)
    assert isinstance(validation["warnings"], list)


def test_validate_with_errors(client: TestClient) -> None:
    """Test validation detects errors in configuration."""
    # Create a config with invalid values
    invalid_config = {
        "name": "invalid-config",
        "data": {
            "name": "Invalid Config",
            "enabled": True,
            "max_requests": 20000,  # Exceeds maximum of 10000
            "timeout_seconds": 0.5,  # Below minimum of 1
            "tags": [],
        },
    }

    create_response = client.post("/api/v1/config", json=invalid_config)
    assert create_response.status_code == 201
    created = create_response.json()
    config_id = created["id"]

    # Validate it
    response = client.get(f"/api/v1/config/{config_id}/$validate")
    assert response.status_code == 200
    validation = response.json()

    # Should have errors
    assert validation["valid"] is False
    assert len(validation["errors"]) > 0
    assert any("max_requests" in err for err in validation["errors"])
    assert any("timeout_seconds" in err for err in validation["errors"])


def test_duplicate_operation(client: TestClient) -> None:
    """Test POST operation to duplicate a configuration."""
    # Get a config to duplicate
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    original_config = configs[0]
    config_id = original_config["id"]

    # Duplicate it
    response = client.post(f"/api/v1/config/{config_id}/$duplicate", params={"new_name": "duplicated-config"})
    assert response.status_code == 201
    duplicate = response.json()

    # Verify duplicate
    assert duplicate["id"] != config_id
    assert duplicate["name"] == "duplicated-config"
    assert duplicate["data"] == original_config["data"]


def test_duplicate_with_existing_name_fails(client: TestClient) -> None:
    """Test duplicating with existing name returns 409."""
    # Get a config to duplicate
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    config_id = configs[0]["id"]

    # Try to duplicate with name that already exists
    response = client.post(
        f"/api/v1/config/{config_id}/$duplicate",
        params={"new_name": "api_rate_limiting"},  # Already exists
    )
    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"].lower()


def test_bulk_toggle_operation(client: TestClient) -> None:
    """Test PATCH collection operation to bulk enable/disable configs."""
    # Disable all configs
    response = client.patch("/api/v1/config/$bulk-toggle", json={"enabled": False, "tag_filter": None})
    assert response.status_code == 200
    result = response.json()

    assert "updated" in result
    assert result["updated"] >= 3  # At least 3 seeded configs updated

    # Verify all are disabled
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    assert all(not c["data"]["enabled"] for c in configs)

    # Re-enable all
    response2 = client.patch("/api/v1/config/$bulk-toggle", json={"enabled": True, "tag_filter": None})
    assert response2.status_code == 200


def test_bulk_toggle_with_tag_filter(client: TestClient) -> None:
    """Test bulk toggle with tag filter."""
    # Toggle only configs with "api" tag (should be api_rate_limiting)
    response = client.patch("/api/v1/config/$bulk-toggle", json={"enabled": False, "tag_filter": "api"})
    assert response.status_code == 200
    result = response.json()

    # Should update at least 1 config with "api" tag
    assert result["updated"] >= 1

    # Verify only api_rate_limiting is disabled
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    api_config = next((c for c in configs if c["name"] == "api_rate_limiting"), None)
    assert api_config is not None
    assert api_config["data"]["enabled"] is False


def test_stats_operation(client: TestClient) -> None:
    """Test GET collection operation to get statistics."""
    response = client.get("/api/v1/config/$stats")
    assert response.status_code == 200
    stats = response.json()

    # Verify stats structure
    assert "total" in stats
    assert "enabled" in stats
    assert "disabled" in stats
    assert "avg_max_requests" in stats
    assert "tags" in stats

    assert stats["total"] >= 3  # At least 3 seeded configs
    assert stats["enabled"] + stats["disabled"] == stats["total"]
    assert isinstance(stats["avg_max_requests"], (int, float))
    assert isinstance(stats["tags"], dict)

    # Verify tag counts
    expected_tags = {"api", "security", "performance", "cache", "experimental", "beta", "new", "test", "updated"}
    assert set(stats["tags"].keys()).issubset(expected_tags)


def test_reset_operation(client: TestClient) -> None:
    """Test POST collection operation to reset all configurations."""
    # First, modify some configs
    list_response = client.get("/api/v1/config")
    configs = list_response.json()
    config_id = configs[0]["id"]

    # Update with different values
    client.patch(f"/api/v1/config/{config_id}/$enable", params={"enabled": False})

    # Reset all
    response = client.post("/api/v1/config/$reset")
    assert response.status_code == 200
    result = response.json()

    assert "reset" in result
    assert result["reset"] >= 3  # At least 3 seeded configs reset

    # Verify configs are reset to defaults (check at least the seeded ones)
    list_response2 = client.get("/api/v1/config")
    configs2 = list_response2.json()

    # Check that at least 3 configs have default values
    default_configs = [
        c
        for c in configs2
        if c["data"]["enabled"] is True
        and c["data"]["max_requests"] == 1000
        and c["data"]["timeout_seconds"] == 30.0
        and c["data"]["tags"] == []
    ]
    assert len(default_configs) >= 3


def test_standard_crud_create(client: TestClient) -> None:
    """Test standard POST to create a config."""
    new_config = {
        "name": "new-feature",
        "data": {
            "name": "New Feature",
            "enabled": True,
            "max_requests": 500,
            "timeout_seconds": 45.0,
            "tags": ["new", "test"],
        },
    }

    response = client.post("/api/v1/config", json=new_config)
    assert response.status_code == 201
    created = response.json()

    assert created["name"] == "new-feature"
    assert created["data"]["max_requests"] == 500
    assert created["data"]["tags"] == ["new", "test"]


def test_standard_crud_update(client: TestClient) -> None:
    """Test standard PUT to update a config."""
    # Create a config
    new_config = {
        "name": "update-test",
        "data": {"name": "Update Test", "enabled": False, "max_requests": 100, "timeout_seconds": 10.0, "tags": []},
    }
    create_response = client.post("/api/v1/config", json=new_config)
    created = create_response.json()
    config_id = created["id"]

    # Update it
    updated_config = {
        "id": config_id,
        "name": "update-test",
        "data": {
            "name": "Updated Test",
            "enabled": True,
            "max_requests": 200,
            "timeout_seconds": 20.0,
            "tags": ["updated"],
        },
    }

    response = client.put(f"/api/v1/config/{config_id}", json=updated_config)
    assert response.status_code == 200
    updated = response.json()

    assert updated["data"]["enabled"] is True
    assert updated["data"]["max_requests"] == 200
    assert updated["data"]["tags"] == ["updated"]


def test_standard_crud_delete(client: TestClient) -> None:
    """Test standard DELETE to remove a config."""
    # Create a config
    new_config = {
        "name": "delete-test",
        "data": {"name": "Delete Test", "enabled": True, "max_requests": 100, "timeout_seconds": 10.0, "tags": []},
    }
    create_response = client.post("/api/v1/config", json=new_config)
    created = create_response.json()
    config_id = created["id"]

    # Delete it
    response = client.delete(f"/api/v1/config/{config_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/v1/config/{config_id}")
    assert get_response.status_code == 404


def test_validate_not_found(client: TestClient) -> None:
    """Test validate operation on non-existent config returns 404."""
    response = client.get("/api/v1/config/01K72P5N5KCRM6MD3BRE4P0999/$validate")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_duplicate_not_found(client: TestClient) -> None:
    """Test duplicate operation on non-existent config returns 404."""
    response = client.post("/api/v1/config/01K72P5N5KCRM6MD3BRE4P0999/$duplicate", params={"new_name": "test"})
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
