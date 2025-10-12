"""Tests to improve coverage of chapkit.core modules."""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from chapkit.core import BaseManager, BaseRepository, Database, Entity, EntityIn, EntityOut
from chapkit.core.logging import add_request_context, clear_request_context, get_logger, reset_request_context


class CustomEntity(Entity):
    """Test entity for custom behavior."""

    __tablename__ = "custom_entities"
    name: Mapped[str]
    value: Mapped[int]


class CustomEntityIn(EntityIn):
    """Input schema for custom entity."""

    name: str
    value: int


class CustomEntityOut(EntityOut):
    """Output schema for custom entity."""

    name: str
    value: int


class CustomEntityRepository(BaseRepository):
    """Repository for custom entity."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        super().__init__(session, CustomEntity)


class CustomEntityManager(BaseManager):
    """Manager with custom field assignment logic."""

    def __init__(self, repo: CustomEntityRepository) -> None:
        """Initialize manager."""
        super().__init__(repo, CustomEntity, CustomEntityOut)

    def _should_assign_field(self, field: str, value: object) -> bool:
        """Override to skip assignment of 'name' field when value is 'skip'."""
        if field == "name" and value == "skip":
            return False
        return True


async def test_database_custom_alembic_dir():
    """Test Database with custom alembic directory."""
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy the real alembic directory structure
        real_alembic_dir = Path(__file__).parent.parent / "alembic"
        custom_alembic_dir = Path(tmpdir) / "custom_alembic"
        shutil.copytree(real_alembic_dir, custom_alembic_dir)

        # Create database with custom alembic dir (auto_migrate=True to hit line 78)
        db_path = Path(tmpdir) / "test.db"
        db = Database(f"sqlite+aiosqlite:///{db_path}", alembic_dir=custom_alembic_dir, auto_migrate=True)

        await db.init()
        await db.dispose()

        # Verify database was created and migrations ran
        assert db_path.exists()


async def test_manager_should_assign_field_returns_false():
    """Test BaseManager when _should_assign_field returns False."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()

    async with db.session() as session:
        repo = CustomEntityRepository(session)
        manager = CustomEntityManager(repo)

        # Create entity
        result = await manager.save(CustomEntityIn(name="original", value=1))
        entity_id = result.id

        # Update with name="skip" should skip the name field
        updated = await manager.save(CustomEntityIn(id=entity_id, name="skip", value=2))

        # Name should still be "original" because "skip" was filtered out
        assert updated.name == "original"
        assert updated.value == 2

    await db.dispose()


async def test_manager_should_assign_field_returns_false_bulk():
    """Test BaseManager save_all when _should_assign_field returns False."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()

    async with db.session() as session:
        repo = CustomEntityRepository(session)
        manager = CustomEntityManager(repo)

        # Create entities
        result1 = await manager.save(CustomEntityIn(name="original1", value=1))
        result2 = await manager.save(CustomEntityIn(name="original2", value=2))

        # Bulk update with name="skip" should skip the name field
        updated = await manager.save_all(
            [
                CustomEntityIn(id=result1.id, name="skip", value=10),
                CustomEntityIn(id=result2.id, name="skip", value=20),
            ]
        )

        # Names should still be "original*" because "skip" was filtered out
        assert updated[0].name == "original1"
        assert updated[0].value == 10
        assert updated[1].name == "original2"
        assert updated[1].value == 20

    await db.dispose()


async def test_manager_find_paginated():
    """Test manager find_paginated returns tuple correctly."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()

    async with db.session() as session:
        repo = CustomEntityRepository(session)
        manager = CustomEntityManager(repo)

        # Create multiple entities
        for i in range(5):
            await manager.save(CustomEntityIn(name=f"entity_{i}", value=i))

        # Test pagination
        results, total = await manager.find_paginated(page=1, size=2)

        assert len(results) == 2
        assert total == 5
        assert isinstance(results, list)
        assert isinstance(total, int)

    await db.dispose()


def test_logging_clear_request_context():
    """Test clear_request_context removes specific keys."""
    # Add some context
    add_request_context(request_id="123", user_id="456", trace_id="789")

    # Clear specific keys
    clear_request_context("user_id", "trace_id")

    # Reset to clean up
    reset_request_context()


def test_logging_get_logger_with_name():
    """Test get_logger with explicit name."""
    logger = get_logger("test.module")
    assert logger is not None

    # Test logging functionality
    logger.info("test_message", key="value")


async def test_scheduler_duplicate_job_error():
    """Test scheduler raises error when duplicate job ID exists."""
    from unittest.mock import patch

    from chapkit.core.scheduler import AIOJobScheduler

    scheduler = AIOJobScheduler()

    # Create a job
    async def dummy_job():
        return "result"

    job_id = await scheduler.add_job(dummy_job)

    # Mock ULID() to return the same job_id to trigger duplicate check at line 120
    with patch("chapkit.core.scheduler.ULID", return_value=job_id):
        with pytest.raises(RuntimeError, match="already scheduled"):
            await scheduler.add_job(dummy_job)


async def test_scheduler_wait_job_not_found():
    """Test scheduler wait raises KeyError for non-existent job."""
    from ulid import ULID

    from chapkit.core.scheduler import AIOJobScheduler

    scheduler = AIOJobScheduler()

    # Try to wait for a job that was never added
    fake_job_id = ULID()
    with pytest.raises(KeyError, match="Job not found"):
        await scheduler.wait(fake_job_id)
