"""System information router."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from pydantic import BaseModel, Field

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
