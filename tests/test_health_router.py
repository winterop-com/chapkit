"""Tests for health check router."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chapkit.core.api.routers.health import CheckResult, HealthRouter, HealthState, HealthStatus


@pytest.fixture
def app_no_checks() -> FastAPI:
    """FastAPI app with health router but no checks."""
    app = FastAPI()
    health_router = HealthRouter.create(prefix="/health", tags=["health"])
    app.include_router(health_router)
    return app


@pytest.fixture
def app_with_checks() -> FastAPI:
    """FastAPI app with health router and custom checks."""

    async def check_healthy() -> tuple[HealthState, str | None]:
        return (HealthState.HEALTHY, None)

    async def check_degraded() -> tuple[HealthState, str | None]:
        return (HealthState.DEGRADED, "Partial outage")

    async def check_unhealthy() -> tuple[HealthState, str | None]:
        return (HealthState.UNHEALTHY, "Service down")

    async def check_exception() -> tuple[HealthState, str | None]:
        raise RuntimeError("Check failed")

    app = FastAPI()
    health_router = HealthRouter.create(
        prefix="/health",
        tags=["health"],
        checks={
            "healthy_check": check_healthy,
            "degraded_check": check_degraded,
            "unhealthy_check": check_unhealthy,
            "exception_check": check_exception,
        },
    )
    app.include_router(health_router)
    return app


def test_health_check_no_checks(app_no_checks: FastAPI) -> None:
    """Test health check endpoint with no custom checks returns healthy."""
    client = TestClient(app_no_checks)
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "checks" not in data or data["checks"] is None


def test_health_check_with_checks(app_with_checks: FastAPI) -> None:
    """Test health check endpoint with custom checks aggregates results."""
    client = TestClient(app_with_checks)
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()

    # Overall status should be unhealthy (worst state)
    assert data["status"] == "unhealthy"

    # Verify individual check results
    checks = data["checks"]
    assert checks["healthy_check"]["state"] == "healthy"
    assert "message" not in checks["healthy_check"]  # None excluded

    assert checks["degraded_check"]["state"] == "degraded"
    assert checks["degraded_check"]["message"] == "Partial outage"

    assert checks["unhealthy_check"]["state"] == "unhealthy"
    assert checks["unhealthy_check"]["message"] == "Service down"

    # Exception should be caught and reported as unhealthy
    assert checks["exception_check"]["state"] == "unhealthy"
    assert "Check failed" in checks["exception_check"]["message"]


def test_health_state_enum() -> None:
    """Test HealthState enum values."""
    assert HealthState.HEALTHY.value == "healthy"
    assert HealthState.DEGRADED.value == "degraded"
    assert HealthState.UNHEALTHY.value == "unhealthy"


def test_check_result_model() -> None:
    """Test CheckResult model."""
    result = CheckResult(state=HealthState.HEALTHY, message=None)
    assert result.state == HealthState.HEALTHY
    assert result.message is None

    result_with_msg = CheckResult(state=HealthState.UNHEALTHY, message="Error occurred")
    assert result_with_msg.state == HealthState.UNHEALTHY
    assert result_with_msg.message == "Error occurred"


def test_health_status_model() -> None:
    """Test HealthStatus model."""
    status = HealthStatus(status=HealthState.HEALTHY)
    assert status.status == HealthState.HEALTHY
    assert status.checks is None

    checks = {"test": CheckResult(state=HealthState.HEALTHY, message=None)}
    status_with_checks = HealthStatus(status=HealthState.HEALTHY, checks=checks)
    assert status_with_checks.status == HealthState.HEALTHY
    assert status_with_checks.checks == checks


def test_health_check_aggregation_priority() -> None:
    """Test that unhealthy > degraded > healthy in aggregation."""

    async def check_healthy() -> tuple[HealthState, str | None]:
        return (HealthState.HEALTHY, None)

    async def check_degraded() -> tuple[HealthState, str | None]:
        return (HealthState.DEGRADED, "Warning")

    # Only healthy checks -> overall healthy
    app = FastAPI()
    router = HealthRouter.create(prefix="/health", tags=["health"], checks={"healthy": check_healthy})
    app.include_router(router)

    client = TestClient(app)
    response = client.get("/health/")
    assert response.json()["status"] == "healthy"

    # Healthy + degraded -> overall degraded
    app2 = FastAPI()
    router2 = HealthRouter.create(
        prefix="/health", tags=["health"], checks={"healthy": check_healthy, "degraded": check_degraded}
    )
    app2.include_router(router2)

    client2 = TestClient(app2)
    response = client2.get("/health/")
    assert response.json()["status"] == "degraded"
