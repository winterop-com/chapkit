"""Integration tests for ServiceBuilder app system."""

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from chapkit.core.api import BaseServiceBuilder, ServiceInfo


@pytest.fixture
def app_directory(tmp_path: Path) -> Path:
    """Create test app directory structure."""
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()

    # Create dashboard app
    dashboard_dir = apps_dir / "dashboard"
    dashboard_dir.mkdir()
    (dashboard_dir / "manifest.json").write_text(
        json.dumps({"name": "Dashboard", "version": "1.0.0", "prefix": "/dashboard"})
    )
    (dashboard_dir / "index.html").write_text("<html><body>Dashboard App</body></html>")
    (dashboard_dir / "style.css").write_text("body { color: blue; }")

    # Create admin app
    admin_dir = apps_dir / "admin"
    admin_dir.mkdir()
    (admin_dir / "manifest.json").write_text(json.dumps({"name": "Admin", "version": "2.0.0", "prefix": "/admin"}))
    (admin_dir / "index.html").write_text("<html><body>Admin App</body></html>")

    return apps_dir


def test_service_builder_with_single_app(app_directory: Path):
    """Test mounting a single app."""
    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_app(str(app_directory / "dashboard"))
        .build()
    )

    with TestClient(app) as client:
        # App should be accessible
        response = client.get("/dashboard/")
        assert response.status_code == 200
        assert b"Dashboard App" in response.content

        # CSS should be accessible
        response = client.get("/dashboard/style.css")
        assert response.status_code == 200
        assert b"color: blue" in response.content


def test_service_builder_with_prefix_override(app_directory: Path):
    """Test mounting app with custom prefix."""
    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_app(str(app_directory / "dashboard"), prefix="/custom")
        .build()
    )

    with TestClient(app) as client:
        # App should be at custom prefix
        response = client.get("/custom/")
        assert response.status_code == 200
        assert b"Dashboard App" in response.content

        # Original prefix should not work
        response = client.get("/dashboard/")
        assert response.status_code == 404


def test_service_builder_with_multiple_apps(app_directory: Path):
    """Test mounting multiple apps."""
    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_app(str(app_directory / "dashboard"))
        .with_app(str(app_directory / "admin"))
        .build()
    )

    with TestClient(app) as client:
        # Both apps should be accessible
        dashboard_response = client.get("/dashboard/")
        assert dashboard_response.status_code == 200
        assert b"Dashboard App" in dashboard_response.content

        admin_response = client.get("/admin/")
        assert admin_response.status_code == 200
        assert b"Admin App" in admin_response.content


def test_service_builder_with_apps_autodiscovery(app_directory: Path):
    """Test auto-discovering apps from directory."""
    app = BaseServiceBuilder(info=ServiceInfo(display_name="Test Service")).with_apps(str(app_directory)).build()

    with TestClient(app) as client:
        # Both discovered apps should be accessible
        dashboard_response = client.get("/dashboard/")
        assert dashboard_response.status_code == 200
        assert b"Dashboard App" in dashboard_response.content

        admin_response = client.get("/admin/")
        assert admin_response.status_code == 200
        assert b"Admin App" in admin_response.content


def test_service_builder_apps_with_api_routes(app_directory: Path):
    """Test that apps don't interfere with API routes."""
    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_health()
        .with_system()
        .with_app(str(app_directory / "dashboard"))
        .build()
    )

    with TestClient(app) as client:
        # API routes should work
        health_response = client.get("/health")
        assert health_response.status_code == 200

        system_response = client.get("/api/v1/system")
        assert system_response.status_code == 200

        # App should also work
        app_response = client.get("/dashboard/")
        assert app_response.status_code == 200
        assert b"Dashboard App" in app_response.content


def test_service_builder_apps_override_semantics(app_directory: Path):
    """Test that duplicate prefixes use last-wins semantics."""
    # Mount dashboard twice - second should override first
    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_app(str(app_directory / "dashboard"))
        .with_app(str(app_directory / "admin"), prefix="/dashboard")  # Override with admin
        .build()
    )

    with TestClient(app) as client:
        # Should serve admin app content (not dashboard)
        response = client.get("/dashboard/")
        assert response.status_code == 200
        assert b"Admin App" in response.content


def test_service_builder_apps_api_prefix_blocked(app_directory: Path):
    """Test that apps cannot mount at /api.**."""
    bad_app_dir = app_directory / "bad"
    bad_app_dir.mkdir()
    (bad_app_dir / "manifest.json").write_text(json.dumps({"name": "Bad", "version": "1.0.0", "prefix": "/api/bad"}))
    (bad_app_dir / "index.html").write_text("<html>Bad</html>")

    with pytest.raises(ValueError, match="prefix cannot be '/api'"):
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service")).with_app(str(bad_app_dir)).build()


def test_service_builder_apps_root_mount_works(app_directory: Path):
    """Test that root-mounted apps work correctly (without landing page)."""
    # Create root app with subdirectory structure
    root_app_dir = app_directory / "root"
    root_app_dir.mkdir()
    (root_app_dir / "manifest.json").write_text(json.dumps({"name": "Root", "version": "1.0.0", "prefix": "/"}))
    (root_app_dir / "index.html").write_text("<html><body>Root App Index</body></html>")

    # Create about subdirectory
    about_dir = root_app_dir / "about"
    about_dir.mkdir()
    (about_dir / "index.html").write_text("<html><body>About Page</body></html>")

    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_health()
        .with_system()
        .with_app(str(root_app_dir))
        .build()
    )

    with TestClient(app) as client:
        # API routes should work (routes take precedence over mounts)
        health_response = client.get("/health")
        assert health_response.status_code == 200

        system_response = client.get("/api/v1/system")
        assert system_response.status_code == 200

        info_response = client.get("/api/v1/info")
        assert info_response.status_code == 200

        # Root path serves app
        root_response = client.get("/")
        assert root_response.status_code == 200
        assert b"Root App Index" in root_response.content

        # App subdirectories work
        about_response = client.get("/about")
        assert about_response.status_code == 200
        assert b"About Page" in about_response.content


def test_service_builder_apps_root_override_landing_page(app_directory: Path):
    """Test that root apps can override landing page (last wins)."""
    root_app_dir = app_directory / "root"
    root_app_dir.mkdir()
    (root_app_dir / "manifest.json").write_text(json.dumps({"name": "Custom Root", "version": "1.0.0", "prefix": "/"}))
    (root_app_dir / "index.html").write_text("<html><body>Custom Root App</body></html>")

    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_landing_page()  # Mount built-in landing page first
        .with_app(str(root_app_dir))  # Override with custom root app
        .build()
    )

    with TestClient(app) as client:
        # Should serve custom root app (not landing page)
        response = client.get("/")
        assert response.status_code == 200
        assert b"Custom Root App" in response.content
        assert b"chapkit" not in response.content.lower()  # Not landing page


def test_service_builder_html_mode_serves_index_for_subdirs(app_directory: Path):
    """Test that html=True mode serves index.html for directory paths."""
    dashboard_dir = app_directory / "dashboard"
    subdir = dashboard_dir / "subdir"
    subdir.mkdir()
    (subdir / "index.html").write_text("<html>Subdir Index</html>")

    app = BaseServiceBuilder(info=ServiceInfo(display_name="Test Service")).with_app(str(dashboard_dir)).build()

    with TestClient(app) as client:
        # Requesting /dashboard/subdir/ should serve subdir/index.html
        response = client.get("/dashboard/subdir/")
        assert response.status_code == 200
        assert b"Subdir Index" in response.content


def test_service_builder_apps_404_for_missing_files(app_directory: Path):
    """Test that missing files return 404."""
    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_app(str(app_directory / "dashboard"))
        .build()
    )

    with TestClient(app) as client:
        response = client.get("/dashboard/nonexistent.html")
        assert response.status_code == 404


def test_service_builder_apps_mount_order(app_directory: Path):
    """Test that apps are mounted after routers."""
    # Create an app that would conflict if mounted before routers
    api_like_app = app_directory / "api-like"
    api_like_app.mkdir()
    (api_like_app / "manifest.json").write_text(
        json.dumps({"name": "API Like", "version": "1.0.0", "prefix": "/status"})
    )
    (api_like_app / "index.html").write_text("<html>App Status</html>")

    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_health(prefix="/status")  # Mount health at /status
        .with_app(str(api_like_app))  # Try to mount app at /status (should fail)
        .build()
    )

    with TestClient(app) as client:
        # Health endpoint should take precedence
        response = client.get("/status")
        assert response.status_code == 200
        # Should be JSON health response, not HTML
        assert response.headers["content-type"].startswith("application/json")


def test_service_builder_apps_with_custom_routers(app_directory: Path):
    """Test apps work alongside custom routers."""
    from fastapi import APIRouter

    custom_router = APIRouter(prefix="/custom", tags=["Custom"])

    @custom_router.get("/endpoint")
    async def custom_endpoint() -> dict[str, str]:
        return {"message": "custom"}

    app = (
        BaseServiceBuilder(info=ServiceInfo(display_name="Test Service"))
        .with_app(str(app_directory / "dashboard"))
        .include_router(custom_router)
        .build()
    )

    with TestClient(app) as client:
        # Custom router should work
        custom_response = client.get("/custom/endpoint")
        assert custom_response.status_code == 200
        assert custom_response.json() == {"message": "custom"}

        # App should work
        app_response = client.get("/dashboard/")
        assert app_response.status_code == 200
        assert b"Dashboard App" in app_response.content
