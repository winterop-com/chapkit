"""App system for hosting static web applications."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from chapkit.core.logging import get_logger

logger = get_logger(__name__)


class AppManifest(BaseModel):
    """App manifest configuration."""

    name: str = Field(description="Human-readable app name")
    version: str = Field(description="Semantic version")
    prefix: str = Field(description="URL prefix for mounting")
    description: str | None = Field(default=None, description="App description")
    author: str | None = Field(default=None, description="Author name")
    entry: str = Field(default="index.html", description="Entry point filename")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """Validate mount prefix format."""
        if not v.startswith("/"):
            raise ValueError("prefix must start with '/'")
        if ".." in v:
            raise ValueError("prefix cannot contain '..'")
        if v.startswith("/api/") or v == "/api":
            raise ValueError("prefix cannot be '/api' or start with '/api/'")
        return v


@dataclass
class App:
    """Represents a loaded app with manifest and directory."""

    manifest: AppManifest
    directory: Path
    prefix: str  # May differ from manifest if overridden
    is_package: bool  # True if loaded from package resources


class AppLoader:
    """Loads and validates apps from filesystem or package resources."""

    @staticmethod
    def load_app(path: str | Path | tuple[str, str], prefix: str | None = None) -> App:
        """Load and validate app from filesystem path or package resource tuple."""
        # Detect source type and resolve to directory
        if isinstance(path, tuple):
            # Package resource
            dir_path, is_package = AppLoader._resolve_package_path(path)
        else:
            # Filesystem path
            dir_path = Path(path).resolve()
            is_package = False

            if not dir_path.exists():
                raise FileNotFoundError(f"App directory not found: {dir_path}")
            if not dir_path.is_dir():
                raise NotADirectoryError(f"App path is not a directory: {dir_path}")

        # Load and validate manifest
        manifest_path = dir_path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in: {dir_path}")

        with manifest_path.open() as f:
            manifest_data = json.load(f)
        manifest = AppManifest(**manifest_data)

        # Validate entry file exists
        entry_path = dir_path / manifest.entry
        if not entry_path.exists():
            raise FileNotFoundError(f"Entry file '{manifest.entry}' not found in: {dir_path}")

        # Use override or manifest prefix
        final_prefix = prefix if prefix is not None else manifest.prefix

        # Re-validate prefix if overridden
        if prefix is not None:
            validated = AppManifest(
                name=manifest.name,
                version=manifest.version,
                prefix=final_prefix,
            )
            final_prefix = validated.prefix

        return App(
            manifest=manifest,
            directory=dir_path,
            prefix=final_prefix,
            is_package=is_package,
        )

    @staticmethod
    def discover_apps(path: str | Path | tuple[str, str]) -> list[App]:
        """Discover all apps with manifest.json in directory."""
        # Resolve directory
        if isinstance(path, tuple):
            dir_path, _ = AppLoader._resolve_package_path(path)
        else:
            dir_path = Path(path).resolve()

            if not dir_path.exists():
                raise FileNotFoundError(f"Apps directory not found: {dir_path}")
            if not dir_path.is_dir():
                raise NotADirectoryError(f"Apps path is not a directory: {dir_path}")

        # Scan for subdirectories with manifest.json
        apps: list[App] = []
        for subdir in dir_path.iterdir():
            if subdir.is_dir() and (subdir / "manifest.json").exists():
                try:
                    # Determine if we're in a package context
                    if isinstance(path, tuple):
                        # Build tuple path for subdirectory
                        package_name: str = path[0]
                        base_path: str = path[1]
                        subdir_name = subdir.name
                        subpath = f"{base_path}/{subdir_name}" if base_path else subdir_name
                        app = AppLoader.load_app((package_name, subpath))
                    else:
                        app = AppLoader.load_app(subdir)
                    apps.append(app)
                except Exception as e:
                    # Log but don't fail discovery for invalid apps
                    logger.warning(
                        "app.discovery.failed",
                        directory=str(subdir),
                        error=str(e),
                    )

        return apps

    @staticmethod
    def _resolve_package_path(package_tuple: tuple[str, str]) -> tuple[Path, bool]:
        """Resolve package resource tuple to filesystem path."""
        package_name, subpath = package_tuple

        try:
            spec = importlib.util.find_spec(package_name)
        except (ModuleNotFoundError, ValueError) as e:
            raise ValueError(f"Package '{package_name}' could not be found") from e

        if spec is None or spec.origin is None:
            raise ValueError(f"Package '{package_name}' could not be found")

        # Resolve to package directory
        package_dir = Path(spec.origin).parent
        app_dir = package_dir / subpath

        if not app_dir.exists():
            raise FileNotFoundError(f"App path '{subpath}' not found in package '{package_name}'")
        if not app_dir.is_dir():
            raise NotADirectoryError(f"App path '{subpath}' in package '{package_name}' is not a directory")

        return app_dir, True
