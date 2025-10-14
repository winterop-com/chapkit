"""Tests for monitoring_api example using TestClient.

Tests use FastAPI's TestClient instead of running a separate server.
Validates monitoring setup with OpenTelemetry and Prometheus metrics.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from examples.monitoring_api import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient for testing with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient) -> None:
    """Test health check returns healthy status."""
    response = client.get("/health")
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


def test_metrics_endpoint(client: TestClient) -> None:
    """Test Prometheus metrics endpoint returns metrics in text format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    # Verify Prometheus format
    content = response.text
    assert "# HELP" in content
    assert "# TYPE" in content

    # Verify some expected metrics exist
    assert "python_gc_objects_collected_total" in content or "python_info" in content


def test_service_metadata(client: TestClient) -> None:
    """Test service metadata is available in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    info = schema["info"]
    assert info["title"] == "Monitoring Example Service"
    assert info["version"] == "1.0.0"


def test_config_endpoints_exist(client: TestClient) -> None:
    """Test that config endpoints are available."""
    response = client.get("/api/v1/configs")
    assert response.status_code == 200
    data = response.json()
    # Should return empty list or paginated response initially
    assert isinstance(data, (list, dict))


def test_config_schema_endpoint(client: TestClient) -> None:
    """Test config schema endpoint returns Config entity schema with AppConfig data."""
    response = client.get("/api/v1/configs/$schema")
    assert response.status_code == 200
    schema = response.json()
    assert "properties" in schema
    # Schema includes Config entity fields (id, name, created_at, data)
    assert "id" in schema["properties"]
    assert "name" in schema["properties"]
    assert "data" in schema["properties"]
    # The 'data' field references AppConfig schema
    data_ref = schema["properties"]["data"]
    assert "$ref" in data_ref
    # Check $defs for AppConfig schema
    assert "$defs" in schema
    assert "AppConfig" in schema["$defs"]
    app_config_schema = schema["$defs"]["AppConfig"]
    assert "api_key" in app_config_schema["properties"]
    assert "max_connections" in app_config_schema["properties"]


def test_openapi_schema(client: TestClient) -> None:
    """Test OpenAPI schema includes all expected endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    paths = schema["paths"]

    # Verify operational endpoints at root level
    assert "/health" in paths
    assert "/api/v1/system" in paths
    assert "/metrics" in paths

    # Verify API endpoints are versioned
    assert "/api/v1/configs" in paths
    assert "/api/v1/configs/$schema" in paths
