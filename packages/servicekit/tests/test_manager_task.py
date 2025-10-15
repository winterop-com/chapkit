"""Tests for TaskManager error handling and edge cases."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from servicekit import ArtifactManager, Task, TaskManager, TaskRepository
from servicekit.core import Database, JobScheduler
from ulid import ULID


@pytest.mark.asyncio
async def test_execute_task_without_scheduler() -> None:
    """Test execute_task raises error when scheduler not configured."""
    mock_repo = Mock(spec=TaskRepository)
    manager = TaskManager(repo=mock_repo, scheduler=None, database=None, artifact_manager=None)

    with pytest.raises(ValueError, match="Task execution requires a scheduler"):
        await manager.execute_task(ULID())


@pytest.mark.asyncio
async def test_execute_task_without_artifact_manager() -> None:
    """Test execute_task raises error when artifact manager not configured."""
    mock_repo = Mock(spec=TaskRepository)
    mock_scheduler = Mock(spec=JobScheduler)

    manager = TaskManager(
        repo=mock_repo,
        scheduler=mock_scheduler,
        database=None,
        artifact_manager=None,
    )

    with pytest.raises(ValueError, match="Task execution requires artifacts"):
        await manager.execute_task(ULID())


@pytest.mark.asyncio
async def test_execute_task_not_found() -> None:
    """Test execute_task raises error for non-existent task."""
    mock_repo = Mock(spec=TaskRepository)
    mock_repo.find_by_id = AsyncMock(return_value=None)

    mock_scheduler = Mock(spec=JobScheduler)
    mock_artifact_manager = Mock(spec=ArtifactManager)

    manager = TaskManager(
        repo=mock_repo,
        scheduler=mock_scheduler,
        database=None,
        artifact_manager=mock_artifact_manager,
    )

    task_id = ULID()
    with pytest.raises(ValueError, match=f"Task {task_id} not found"):
        await manager.execute_task(task_id)

    mock_repo.find_by_id.assert_called_once_with(task_id)


@pytest.mark.asyncio
async def test_execute_task_submits_to_scheduler() -> None:
    """Test execute_task successfully submits job to scheduler."""
    task_id = ULID()
    job_id = ULID()

    mock_task = Mock(spec=Task)
    mock_task.id = task_id
    mock_task.command = "echo test"

    mock_repo = Mock(spec=TaskRepository)
    mock_repo.find_by_id = AsyncMock(return_value=mock_task)

    mock_scheduler = Mock(spec=JobScheduler)
    mock_scheduler.add_job = AsyncMock(return_value=job_id)

    mock_artifact_manager = Mock(spec=ArtifactManager)

    manager = TaskManager(
        repo=mock_repo,
        scheduler=mock_scheduler,
        database=None,
        artifact_manager=mock_artifact_manager,
    )

    result = await manager.execute_task(task_id)

    assert result == job_id
    mock_repo.find_by_id.assert_called_once_with(task_id)
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.asyncio
async def test_execute_command_without_database() -> None:
    """Test _execute_command raises error when database not configured."""
    mock_repo = Mock(spec=TaskRepository)
    manager = TaskManager(repo=mock_repo, scheduler=None, database=None, artifact_manager=None)

    with pytest.raises(RuntimeError, match="Database instance required"):
        await manager._execute_command(ULID())


@pytest.mark.asyncio
async def test_execute_command_without_artifact_manager() -> None:
    """Test _execute_command raises error when artifact manager not configured."""
    mock_repo = Mock(spec=TaskRepository)
    mock_database = Mock(spec=Database)

    manager = TaskManager(
        repo=mock_repo,
        scheduler=None,
        database=mock_database,
        artifact_manager=None,
    )

    with pytest.raises(RuntimeError, match="ArtifactManager instance required"):
        await manager._execute_command(ULID())


@pytest.mark.asyncio
async def test_execute_command_task_not_found() -> None:
    """Test _execute_command raises error for non-existent task."""
    task_id = ULID()

    # Mock session context manager
    mock_session = Mock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Mock task repo that returns None
    mock_task_repo = Mock(spec=TaskRepository)
    mock_task_repo.find_by_id = AsyncMock(return_value=None)

    # Mock database
    mock_database = Mock(spec=Database)
    mock_database.session = Mock(return_value=mock_session)

    # Patch TaskRepository to return our mock
    with patch(
        "chapkit.modules.task.manager.TaskRepository",
        return_value=mock_task_repo,
    ):
        mock_repo = Mock(spec=TaskRepository)
        mock_artifact_manager = Mock(spec=ArtifactManager)

        manager = TaskManager(
            repo=mock_repo,
            scheduler=None,
            database=mock_database,
            artifact_manager=mock_artifact_manager,
        )

        with pytest.raises(ValueError, match=f"Task {task_id} not found"):
            await manager._execute_command(task_id)
