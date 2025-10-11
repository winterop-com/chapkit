"""Task repository for database access and querying."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from chapkit.core.repository import BaseRepository

from .models import Task


class TaskRepository(BaseRepository[Task, ULID]):
    """Repository for Task template entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize task repository with database session."""
        super().__init__(session, Task)
