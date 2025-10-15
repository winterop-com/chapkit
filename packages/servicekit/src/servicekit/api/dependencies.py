"""Feature-specific FastAPI dependency injection for managers."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from servicekit.core.api.dependencies import get_database, get_scheduler, get_session
from servicekit.modules.artifact import ArtifactManager, ArtifactRepository
from servicekit.modules.config import BaseConfig, ConfigManager, ConfigRepository
from servicekit.modules.task import TaskManager, TaskRepository

# ML module moved to chapkit package
try:
    from servicekit.modules.ml import MLManager  # type: ignore
except ImportError:
    MLManager = None  # type: ignore


async def get_config_manager(session: Annotated[AsyncSession, Depends(get_session)]) -> ConfigManager[BaseConfig]:
    """Get a config manager instance for dependency injection."""
    repo = ConfigRepository(session)
    return ConfigManager[BaseConfig](repo, BaseConfig)


async def get_artifact_manager(session: Annotated[AsyncSession, Depends(get_session)]) -> ArtifactManager:
    """Get an artifact manager instance for dependency injection."""
    artifact_repo = ArtifactRepository(session)
    config_repo = ConfigRepository(session)
    return ArtifactManager(artifact_repo, config_repo=config_repo)


async def get_task_manager(
    session: Annotated[AsyncSession, Depends(get_session)],
    artifact_manager: Annotated[ArtifactManager, Depends(get_artifact_manager)],
) -> TaskManager:
    """Get a task manager instance for dependency injection."""
    from servicekit.core import Database
    from servicekit.core.scheduler import JobScheduler

    repo = TaskRepository(session)

    # Get scheduler if available
    scheduler: JobScheduler | None
    try:
        scheduler = get_scheduler()
    except RuntimeError:
        scheduler = None

    # Get database if available
    database: Database | None
    try:
        database = get_database()
    except RuntimeError:
        database = None

    return TaskManager(repo, scheduler, database, artifact_manager)


async def get_ml_manager() -> MLManager:
    """Get an ML manager instance for dependency injection.

    Note: This is a placeholder. The actual dependency is built by ServiceBuilder
    with the runner in closure, then overridden via app.dependency_overrides.
    """
    raise RuntimeError("ML manager dependency not configured. Use ServiceBuilder.with_ml() to enable ML operations.")
