"""Tests for dependency injection utilities."""

from __future__ import annotations

import pytest

from servicekit import SqliteDatabaseBuilder
from servicekit.core.api.dependencies import get_database, get_scheduler, set_database, set_scheduler


def test_get_database_uninitialized() -> None:
    """Test get_database raises error when database is not initialized."""
    # Reset global database state
    import servicekit.core.api.dependencies as deps

    original_db = deps._database
    deps._database = None

    try:
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_database()
    finally:
        # Restore original state
        deps._database = original_db


async def test_set_and_get_database() -> None:
    """Test setting and getting the database instance."""
    db = SqliteDatabaseBuilder.in_memory().build()
    await db.init()

    try:
        set_database(db)
        retrieved_db = get_database()
        assert retrieved_db is db
    finally:
        await db.dispose()


async def test_get_config_manager() -> None:
    """Test get_config_manager returns a ConfigManager instance."""
    from servicekit import ConfigManager
    from servicekit.api.dependencies import get_config_manager
    from servicekit.core.api.dependencies import get_session

    db = SqliteDatabaseBuilder.in_memory().build()
    await db.init()

    try:
        set_database(db)

        # Use the session generator
        async for session in get_session(db):
            manager = await get_config_manager(session)
            assert isinstance(manager, ConfigManager)
            break
    finally:
        await db.dispose()


async def test_get_artifact_manager() -> None:
    """Test get_artifact_manager returns an ArtifactManager instance."""
    from servicekit import ArtifactManager
    from servicekit.api.dependencies import get_artifact_manager
    from servicekit.core.api.dependencies import get_session

    db = SqliteDatabaseBuilder.in_memory().build()
    await db.init()

    try:
        set_database(db)

        # Use the session generator
        async for session in get_session(db):
            manager = await get_artifact_manager(session)
            assert isinstance(manager, ArtifactManager)
            break
    finally:
        await db.dispose()


def test_get_scheduler_uninitialized() -> None:
    """Test get_scheduler raises error when scheduler is not initialized."""
    # Reset global scheduler state
    import servicekit.core.api.dependencies as deps

    original_scheduler = deps._scheduler
    deps._scheduler = None

    try:
        with pytest.raises(RuntimeError, match="Scheduler not initialized"):
            get_scheduler()
    finally:
        # Restore original state
        deps._scheduler = original_scheduler


def test_set_and_get_scheduler() -> None:
    """Test setting and getting the scheduler instance."""
    from unittest.mock import Mock

    from servicekit.core import JobScheduler

    # Create a mock scheduler since JobScheduler is abstract
    scheduler = Mock(spec=JobScheduler)

    try:
        set_scheduler(scheduler)
        retrieved_scheduler = get_scheduler()
        assert retrieved_scheduler is scheduler
    finally:
        # Reset global state
        import servicekit.core.api.dependencies as deps

        deps._scheduler = None


async def test_get_task_manager_without_scheduler_and_database() -> None:
    """Test get_task_manager handles missing scheduler and database gracefully."""
    from servicekit.api.dependencies import get_task_manager
    from servicekit.core.api.dependencies import get_session

    db = SqliteDatabaseBuilder.in_memory().build()
    await db.init()

    try:
        set_database(db)

        # Reset scheduler and database to trigger RuntimeError paths
        import servicekit.core.api.dependencies as deps

        original_scheduler = deps._scheduler
        original_db = deps._database
        deps._scheduler = None
        deps._database = None

        # Use the session generator
        async for session in get_session(db):
            # Create a mock artifact manager
            from servicekit import ArtifactManager, ArtifactRepository

            artifact_repo = ArtifactRepository(session)
            artifact_manager = ArtifactManager(artifact_repo)

            manager = await get_task_manager(session, artifact_manager)
            # Manager should be created even without scheduler/database
            assert manager is not None
            break

        # Restore state
        deps._scheduler = original_scheduler
        deps._database = original_db
    finally:
        await db.dispose()


def test_get_ml_manager_raises_runtime_error() -> None:
    """Test get_ml_manager raises RuntimeError when not configured."""
    from servicekit.api.dependencies import get_ml_manager

    with pytest.raises(RuntimeError, match="ML manager dependency not configured"):
        # This is a sync function that returns a coroutine, but we need to call it
        # The function itself should raise before returning the coroutine
        import asyncio

        asyncio.run(get_ml_manager())
