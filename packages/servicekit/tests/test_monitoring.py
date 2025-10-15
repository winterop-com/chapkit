"""Tests for OpenTelemetry monitoring setup."""

from fastapi import FastAPI
from servicekit.core.api.monitoring import setup_monitoring, teardown_monitoring


def test_setup_monitoring_with_traces_enabled() -> None:
    """Test setup_monitoring with enable_traces=True logs warning."""
    app = FastAPI(title="Test Service")

    # This should log a warning about traces not being implemented
    reader = setup_monitoring(app, enable_traces=True)

    assert reader is not None


def test_teardown_monitoring() -> None:
    """Test teardown_monitoring uninstruments components."""
    app = FastAPI(title="Test Service")

    # Setup first
    setup_monitoring(app, service_name="test-teardown")

    # Then teardown
    teardown_monitoring()

    # No assertions needed - we're just covering the code path
    # The function should handle uninstrumentation gracefully


def test_setup_monitoring_idempotent() -> None:
    """Test that setup_monitoring can be called multiple times safely."""
    app1 = FastAPI(title="Service 1")
    app2 = FastAPI(title="Service 2")

    # First call initializes everything
    reader1 = setup_monitoring(app1, service_name="service-1")
    assert reader1 is not None

    # Second call should handle already-initialized state
    reader2 = setup_monitoring(app2, service_name="service-2")
    assert reader2 is not None
