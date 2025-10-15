"""System information router."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends
from pydantic import BaseModel, Field, TypeAdapter

from ..app import AppInfo, AppManager
from ..dependencies import get_app_manager
from ..router import Router


class SystemInfo(BaseModel):
    """System information response."""

    current_time: datetime = Field(description="Current server time in UTC")
    timezone: str = Field(description="Server timezone")
    python_version: str = Field(description="Python version")
    platform: str = Field(description="Operating system platform")
    hostname: str = Field(description="Server hostname")


class SystemRouter(Router):
    """System information router."""

    def _register_routes(self) -> None:
        """Register system info endpoint."""

        @self.router.get(
            "",
            summary="System information",
            response_model=SystemInfo,
        )
        async def get_system_info() -> SystemInfo:
            return SystemInfo(
                current_time=datetime.now(timezone.utc),
                timezone=str(datetime.now().astimezone().tzinfo),
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                platform=platform.platform(),
                hostname=platform.node(),
            )

        @self.router.get(
            "/apps",
            summary="List installed apps",
            response_model=list[AppInfo],
        )
        async def list_apps(
            app_manager: Annotated[AppManager, Depends(get_app_manager)],
        ) -> list[AppInfo]:
            """List all installed apps with their metadata."""
            return [
                AppInfo(
                    name=app.manifest.name,
                    version=app.manifest.version,
                    prefix=app.prefix,
                    description=app.manifest.description,
                    author=app.manifest.author,
                    entry=app.manifest.entry,
                    is_package=app.is_package,
                )
                for app in app_manager.list()
            ]

        @self.router.get(
            "/apps/$schema",
            summary="Get apps list schema",
            response_model=dict[str, Any],
        )
        async def get_apps_schema() -> dict[str, Any]:
            """Get JSON schema for apps list response."""
            return TypeAdapter(list[AppInfo]).json_schema()
