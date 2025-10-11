"""Generic FastAPI dependency injection for database and scheduler."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chapkit.core import Database
from chapkit.core.scheduler import JobScheduler

# Global database instance - should be initialized at app startup
_database: Database | None = None

# Global scheduler instance - should be initialized at app startup
_scheduler: JobScheduler | None = None


def set_database(database: Database) -> None:
    """Set the global database instance."""
    global _database
    _database = database


def get_database() -> Database:
    """Get the global database instance."""
    if _database is None:
        raise RuntimeError("Database not initialized. Call set_database() during app startup.")
    return _database


async def get_session(db: Annotated[Database, Depends(get_database)]) -> AsyncIterator[AsyncSession]:
    """Get a database session for dependency injection."""
    async with db.session() as session:
        yield session


def set_scheduler(scheduler: JobScheduler) -> None:
    """Set the global scheduler instance."""
    global _scheduler
    _scheduler = scheduler


def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call set_scheduler() during app startup.")
    return _scheduler
