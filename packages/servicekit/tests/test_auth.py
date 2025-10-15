"""Tests for API key authentication middleware and utilities."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from servicekit.core.api.auth import (
    APIKeyMiddleware,
    load_api_keys_from_env,
    load_api_keys_from_file,
    validate_api_key_format,
)


def test_load_api_keys_from_env_single_key(monkeypatch: MonkeyPatch) -> None:
    """Test loading a single API key from environment variable."""
    monkeypatch.setenv("CHAPKIT_API_KEYS", "sk_test_123")
    keys = load_api_keys_from_env("CHAPKIT_API_KEYS")
    assert keys == {"sk_test_123"}


def test_load_api_keys_from_env_multiple_keys(monkeypatch: MonkeyPatch) -> None:
    """Test loading multiple comma-separated keys."""
    monkeypatch.setenv("CHAPKIT_API_KEYS", "sk_test_1,sk_test_2,sk_test_3")
    keys = load_api_keys_from_env("CHAPKIT_API_KEYS")
    assert keys == {"sk_test_1", "sk_test_2", "sk_test_3"}


def test_load_api_keys_from_env_with_spaces(monkeypatch: MonkeyPatch) -> None:
    """Test that spaces around keys are stripped."""
    monkeypatch.setenv("CHAPKIT_API_KEYS", "sk_test_1 , sk_test_2 , sk_test_3")
    keys = load_api_keys_from_env("CHAPKIT_API_KEYS")
    assert keys == {"sk_test_1", "sk_test_2", "sk_test_3"}


def test_load_api_keys_from_env_empty() -> None:
    """Test loading from non-existent environment variable."""
    keys = load_api_keys_from_env("NONEXISTENT_VAR")
    assert keys == set()


def test_load_api_keys_from_env_empty_string(monkeypatch: MonkeyPatch) -> None:
    """Test loading from empty environment variable."""
    monkeypatch.setenv("CHAPKIT_API_KEYS", "")
    keys = load_api_keys_from_env("CHAPKIT_API_KEYS")
    assert keys == set()


def test_load_api_keys_from_file():
    """Test loading API keys from file."""
    with NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("sk_test_1\n")
        f.write("sk_test_2\n")
        f.write("sk_test_3\n")
        temp_path = f.name

    try:
        keys = load_api_keys_from_file(temp_path)
        assert keys == {"sk_test_1", "sk_test_2", "sk_test_3"}
    finally:
        Path(temp_path).unlink()


def test_load_api_keys_from_file_with_comments():
    """Test that comments and empty lines are ignored."""
    with NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("# Comment line\n")
        f.write("sk_test_1\n")
        f.write("\n")  # Empty line
        f.write("sk_test_2\n")
        f.write("# Another comment\n")
        f.write("sk_test_3\n")
        temp_path = f.name

    try:
        keys = load_api_keys_from_file(temp_path)
        assert keys == {"sk_test_1", "sk_test_2", "sk_test_3"}
    finally:
        Path(temp_path).unlink()


def test_load_api_keys_from_file_not_found():
    """Test error when file doesn't exist."""
    with pytest.raises(FileNotFoundError, match="API key file not found"):
        load_api_keys_from_file("/nonexistent/path/keys.txt")


def test_validate_api_key_format_valid():
    """Test validation of valid API key formats."""
    assert validate_api_key_format("sk_prod_a1b2c3d4e5f6g7h8")
    assert validate_api_key_format("sk_dev_1234567890123456")
    assert validate_api_key_format("1234567890123456")  # Min length 16


def test_validate_api_key_format_too_short():
    """Test validation rejects keys shorter than 16 characters."""
    assert not validate_api_key_format("short")
    assert not validate_api_key_format("sk_dev_123")
    assert not validate_api_key_format("123456789012345")  # 15 chars


def test_api_key_middleware_valid_key():
    """Test middleware allows requests with valid API key."""
    app = FastAPI()

    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_valid"},
        header_name="X-API-Key",
        unauthenticated_paths=set(),
    )

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test", headers={"X-API-Key": "sk_test_valid"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_key_middleware_invalid_key():
    """Test middleware rejects requests with invalid API key."""
    from servicekit.core.api.middleware import add_error_handlers

    app = FastAPI()

    # Add error handlers FIRST (before middleware)
    add_error_handlers(app)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    # Add middleware after routes
    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_valid"},
        header_name="X-API-Key",
        unauthenticated_paths=set(),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test", headers={"X-API-Key": "sk_test_invalid"})

    assert response.status_code == 401
    assert response.json()["type"] == "urn:chapkit:error:unauthorized"
    assert "Invalid API key" in response.json()["detail"]


def test_api_key_middleware_missing_key():
    """Test middleware rejects requests without API key."""
    from servicekit.core.api.middleware import add_error_handlers

    app = FastAPI()

    # Add error handlers FIRST (before middleware)
    add_error_handlers(app)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    # Add middleware after routes
    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_valid"},
        header_name="X-API-Key",
        unauthenticated_paths=set(),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test")

    assert response.status_code == 401
    assert response.json()["type"] == "urn:chapkit:error:unauthorized"
    assert "Missing authentication header" in response.json()["detail"]


def test_api_key_middleware_unauthenticated_path():
    """Test middleware allows unauthenticated paths without key."""
    from servicekit.core.api.middleware import add_error_handlers

    app = FastAPI()

    # Add error handlers FIRST (before middleware)
    add_error_handlers(app)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    # Add middleware after routes
    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_valid"},
        header_name="X-API-Key",
        unauthenticated_paths={"/health", "/docs"},
    )

    client = TestClient(app, raise_server_exceptions=False)

    # Unauthenticated path works without key
    response = client.get("/health")
    assert response.status_code == 200

    # Authenticated path requires key
    response = client.get("/test")
    assert response.status_code == 401


def test_api_key_middleware_multiple_valid_keys():
    """Test middleware accepts any of multiple valid keys."""
    app = FastAPI()

    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_1", "sk_test_2", "sk_test_3"},
        header_name="X-API-Key",
        unauthenticated_paths=set(),
    )

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # All three keys should work
    for key in ["sk_test_1", "sk_test_2", "sk_test_3"]:
        response = client.get("/test", headers={"X-API-Key": key})
        assert response.status_code == 200


def test_api_key_middleware_custom_header_name():
    """Test middleware with custom header name."""
    from servicekit.core.api.middleware import add_error_handlers

    app = FastAPI()

    # Add error handlers FIRST (before middleware)
    add_error_handlers(app)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    # Add middleware after routes
    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_valid"},
        header_name="X-Custom-API-Key",
        unauthenticated_paths=set(),
    )

    client = TestClient(app, raise_server_exceptions=False)

    # Default header name shouldn't work
    response = client.get("/test", headers={"X-API-Key": "sk_test_valid"})
    assert response.status_code == 401

    # Custom header name should work
    response = client.get("/test", headers={"X-Custom-API-Key": "sk_test_valid"})
    assert response.status_code == 200


def test_api_key_middleware_attaches_prefix_to_request_state():
    """Test that middleware attaches key prefix to request state."""
    app = FastAPI()

    app.add_middleware(
        APIKeyMiddleware,
        api_keys={"sk_test_valid_key_12345"},
        header_name="X-API-Key",
        unauthenticated_paths=set(),
    )

    @app.get("/test")
    def test_endpoint(request: Request):
        # Check that key prefix is attached to request state
        assert hasattr(request.state, "api_key_prefix")
        assert request.state.api_key_prefix == "sk_test"
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test", headers={"X-API-Key": "sk_test_valid_key_12345"})

    assert response.status_code == 200


def test_service_builder_auth_logging_no_duplicates(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that auth warning is logged only once during startup."""
    from servicekit.core.api import BaseServiceBuilder, ServiceInfo

    # Build app with direct API keys (triggers warning)
    info = ServiceInfo(display_name="Test Service")
    app = BaseServiceBuilder(info=info, include_logging=True).with_auth(api_keys=["sk_dev_test123"]).build()

    # Create test client (triggers startup)
    with TestClient(app):
        pass

    # Capture output
    captured = capsys.readouterr()

    # Count occurrences of the warning message
    warning_count = captured.out.count("Using direct API keys")

    # Should appear exactly once
    assert warning_count == 1, f"Expected 1 warning, found {warning_count}"
