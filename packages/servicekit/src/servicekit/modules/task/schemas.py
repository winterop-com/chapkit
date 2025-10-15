"""Task schemas for reusable command templates."""

from __future__ import annotations

from pydantic import Field

from servicekit.core.schemas import EntityIn, EntityOut


class TaskIn(EntityIn):
    """Input schema for creating or updating task templates."""

    command: str = Field(description="Shell command to execute")


class TaskOut(EntityOut):
    """Output schema for task template entities."""

    command: str = Field(description="Shell command to execute")
