"""Tests for app loading and validation."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from chapkit.core.api.app import App, AppLoader, AppManifest


def test_app_manifest_valid():
    """Test valid app manifest."""
    manifest = AppManifest(
        name="Test App",
        version="1.0.0",
        prefix="/test",
        description="Test description",
        author="Test Author",
        entry="index.html",
    )
    assert manifest.name == "Test App"
    assert manifest.version == "1.0.0"
    assert manifest.prefix == "/test"
    assert manifest.entry == "index.html"


def test_app_manifest_minimal():
    """Test minimal app manifest (only required fields)."""
    manifest = AppManifest(
        name="Minimal App",
        version="1.0.0",
        prefix="/minimal",
    )
    assert manifest.name == "Minimal App"
    assert manifest.entry == "index.html"  # Default
    assert manifest.description is None
    assert manifest.author is None


def test_app_manifest_invalid_prefix_no_slash():
    """Test manifest validation rejects prefix without leading slash."""
    with pytest.raises(ValidationError, match="prefix must start with '/'"):
        AppManifest(
            name="Bad App",
            version="1.0.0",
            prefix="bad",
        )


def test_app_manifest_invalid_prefix_path_traversal():
    """Test manifest validation rejects path traversal in prefix."""
    with pytest.raises(ValidationError, match="prefix cannot contain '..'"):
        AppManifest(
            name="Bad App",
            version="1.0.0",
            prefix="/../etc",
        )


def test_app_manifest_invalid_prefix_api():
    """Test manifest validation rejects /api prefix."""
    with pytest.raises(ValidationError, match="prefix cannot be '/api'"):
        AppManifest(
            name="Bad App",
            version="1.0.0",
            prefix="/api",
        )


def test_app_manifest_invalid_prefix_api_subpath():
    """Test manifest validation rejects /api/** prefix."""
    with pytest.raises(ValidationError, match="prefix cannot be '/api'"):
        AppManifest(
            name="Bad App",
            version="1.0.0",
            prefix="/api/dashboard",
        )


def test_load_app_from_filesystem(tmp_path: Path):
    """Test loading app from filesystem."""
    # Create app structure
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    manifest = {
        "name": "Test App",
        "version": "1.0.0",
        "prefix": "/test",
        "description": "Test app",
    }
    (app_dir / "manifest.json").write_text(json.dumps(manifest))
    (app_dir / "index.html").write_text("<html>Test</html>")

    # Load app
    app = AppLoader.load_app(str(app_dir))

    assert app.manifest.name == "Test App"
    assert app.manifest.prefix == "/test"
    assert app.prefix == "/test"
    assert app.directory == app_dir
    assert not app.is_package


def test_load_app_with_prefix_override(tmp_path: Path):
    """Test loading app with prefix override."""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    manifest = {
        "name": "Test App",
        "version": "1.0.0",
        "prefix": "/original",
    }
    (app_dir / "manifest.json").write_text(json.dumps(manifest))
    (app_dir / "index.html").write_text("<html>Test</html>")

    # Load with override
    app = AppLoader.load_app(str(app_dir), prefix="/overridden")

    assert app.manifest.prefix == "/original"  # Original unchanged
    assert app.prefix == "/overridden"  # Override applied


def test_load_app_custom_entry(tmp_path: Path):
    """Test loading app with custom entry file."""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    manifest = {
        "name": "Test App",
        "version": "1.0.0",
        "prefix": "/test",
        "entry": "main.html",
    }
    (app_dir / "manifest.json").write_text(json.dumps(manifest))
    (app_dir / "main.html").write_text("<html>Test</html>")

    # Load app
    app = AppLoader.load_app(str(app_dir))

    assert app.manifest.entry == "main.html"


def test_load_app_missing_directory(tmp_path: Path):
    """Test loading app from non-existent directory."""
    with pytest.raises(FileNotFoundError, match="App directory not found"):
        AppLoader.load_app(str(tmp_path / "nonexistent"))


def test_load_app_missing_manifest(tmp_path: Path):
    """Test loading app without manifest.json."""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="manifest.json not found"):
        AppLoader.load_app(str(app_dir))


def test_load_app_missing_entry_file(tmp_path: Path):
    """Test loading app without entry file."""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    manifest = {
        "name": "Test App",
        "version": "1.0.0",
        "prefix": "/test",
    }
    (app_dir / "manifest.json").write_text(json.dumps(manifest))
    # No index.html created

    with pytest.raises(FileNotFoundError, match="Entry file 'index.html' not found"):
        AppLoader.load_app(str(app_dir))


def test_load_app_invalid_manifest_json(tmp_path: Path):
    """Test loading app with invalid JSON manifest."""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    (app_dir / "manifest.json").write_text("invalid json{")
    (app_dir / "index.html").write_text("<html>Test</html>")

    with pytest.raises(json.JSONDecodeError):
        AppLoader.load_app(str(app_dir))


def test_load_app_invalid_manifest_schema(tmp_path: Path):
    """Test loading app with manifest missing required fields."""
    app_dir = tmp_path / "test-app"
    app_dir.mkdir()

    manifest = {
        "name": "Test App",
        # Missing version and prefix
    }
    (app_dir / "manifest.json").write_text(json.dumps(manifest))
    (app_dir / "index.html").write_text("<html>Test</html>")

    with pytest.raises(ValidationError):
        AppLoader.load_app(str(app_dir))


def test_discover_apps(tmp_path: Path):
    """Test discovering multiple apps in a directory."""
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()

    # Create app 1
    app1_dir = apps_dir / "app1"
    app1_dir.mkdir()
    (app1_dir / "manifest.json").write_text(json.dumps({"name": "App 1", "version": "1.0.0", "prefix": "/app1"}))
    (app1_dir / "index.html").write_text("<html>App 1</html>")

    # Create app 2
    app2_dir = apps_dir / "app2"
    app2_dir.mkdir()
    (app2_dir / "manifest.json").write_text(json.dumps({"name": "App 2", "version": "1.0.0", "prefix": "/app2"}))
    (app2_dir / "index.html").write_text("<html>App 2</html>")

    # Discover apps
    apps = AppLoader.discover_apps(str(apps_dir))

    assert len(apps) == 2
    app_names = {app.manifest.name for app in apps}
    assert app_names == {"App 1", "App 2"}


def test_discover_apps_ignores_invalid(tmp_path: Path):
    """Test app discovery ignores invalid apps."""
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()

    # Valid app
    valid_dir = apps_dir / "valid"
    valid_dir.mkdir()
    (valid_dir / "manifest.json").write_text(json.dumps({"name": "Valid", "version": "1.0.0", "prefix": "/valid"}))
    (valid_dir / "index.html").write_text("<html>Valid</html>")

    # Invalid app (missing entry file)
    invalid_dir = apps_dir / "invalid"
    invalid_dir.mkdir()
    (invalid_dir / "manifest.json").write_text(
        json.dumps({"name": "Invalid", "version": "1.0.0", "prefix": "/invalid"})
    )
    # No index.html

    # Directory without manifest
    no_manifest_dir = apps_dir / "no-manifest"
    no_manifest_dir.mkdir()
    (no_manifest_dir / "index.html").write_text("<html>No Manifest</html>")

    # Discover apps (should only find valid app)
    apps = AppLoader.discover_apps(str(apps_dir))

    assert len(apps) == 1
    assert apps[0].manifest.name == "Valid"


def test_discover_apps_empty_directory(tmp_path: Path):
    """Test discovering apps in empty directory."""
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()

    apps = AppLoader.discover_apps(str(apps_dir))

    assert len(apps) == 0


def test_discover_apps_missing_directory(tmp_path: Path):
    """Test discovering apps in non-existent directory."""
    with pytest.raises(FileNotFoundError, match="Apps directory not found"):
        AppLoader.discover_apps(str(tmp_path / "nonexistent"))


def test_load_app_from_package():
    """Test loading app from package resources."""
    # Load from chapkit.core.api package (we know this exists)
    # We'll create a test by using an invalid package to test error handling
    with pytest.raises(ValueError, match="Package .* could not be found"):
        AppLoader.load_app(("nonexistent.package", "apps/test"))


def test_app_dataclass():
    """Test App dataclass structure."""
    manifest = AppManifest(
        name="Test",
        version="1.0.0",
        prefix="/test",
    )

    app = App(
        manifest=manifest,
        directory=Path("/tmp/test"),
        prefix="/custom",
        is_package=False,
    )

    assert app.manifest.name == "Test"
    assert app.directory == Path("/tmp/test")
    assert app.prefix == "/custom"
    assert not app.is_package
