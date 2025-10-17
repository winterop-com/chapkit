"""Task manager for reusable command templates with artifact-based execution results."""

from __future__ import annotations

import asyncio
import inspect
import traceback
from typing import Any

from ulid import ULID

from chapkit.core import Database
from chapkit.core.manager import BaseManager
from chapkit.core.scheduler import JobScheduler
from chapkit.modules.artifact import ArtifactIn, ArtifactManager, ArtifactRepository

from .models import Task
from .registry import TaskRegistry
from .repository import TaskRepository
from .schemas import TaskIn, TaskOut


class TaskManager(BaseManager[Task, TaskIn, TaskOut, ULID]):
    """Manager for Task template entities with artifact-based execution."""

    def __init__(
        self,
        repo: TaskRepository,
        scheduler: JobScheduler | None = None,
        database: Database | None = None,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        """Initialize task manager with repository, scheduler, database, and artifact manager."""
        super().__init__(repo, Task, TaskOut)
        self.repo: TaskRepository = repo
        self.scheduler = scheduler
        self.database = database
        self.artifact_manager = artifact_manager

    async def find_all(self, *, enabled: bool | None = None) -> list[TaskOut]:
        """Find all tasks, optionally filtered by enabled status."""
        tasks = await self.repo.find_all(enabled=enabled)
        return [self._to_output_schema(task) for task in tasks]

    async def execute_task(self, task_id: ULID) -> ULID:
        """Execute a task by submitting it to the scheduler and return the job ID."""
        if self.scheduler is None:
            raise ValueError("Task execution requires a scheduler. Use ServiceBuilder.with_jobs() to enable.")

        if self.artifact_manager is None:
            raise ValueError(
                "Task execution requires artifacts. Use ServiceBuilder.with_artifacts() before with_tasks()."
            )

        task = await self.repo.find_by_id(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        # Check if task is enabled
        if not task.enabled:
            raise ValueError(f"Cannot execute disabled task {task_id}")

        # Route based on task type
        if task.task_type == "python":
            job_id = await self.scheduler.add_job(self._execute_python, task_id)
        else:  # shell
            job_id = await self.scheduler.add_job(self._execute_command, task_id)

        return job_id

    async def _execute_command(self, task_id: ULID) -> ULID:
        """Execute command and return artifact_id containing results."""
        if self.database is None:
            raise RuntimeError("Database instance required for task execution")

        if self.artifact_manager is None:
            raise RuntimeError("ArtifactManager instance required for task execution")

        # Fetch task and serialize snapshot before execution
        async with self.database.session() as session:
            task_repo = TaskRepository(session)
            task = await task_repo.find_by_id(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")

            # Capture task snapshot
            task_snapshot = {
                "id": str(task.id),
                "command": task.command,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }

        # Execute command using asyncio subprocess
        process = await asyncio.create_subprocess_shell(
            task.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for completion and capture output
        stdout_bytes, stderr_bytes = await process.communicate()

        # Decode outputs
        stdout_text = stdout_bytes.decode("utf-8") if stdout_bytes else ""
        stderr_text = stderr_bytes.decode("utf-8") if stderr_bytes else ""

        # Create artifact with execution results
        result_data: dict[str, Any] = {
            "task": task_snapshot,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "exit_code": process.returncode,
        }

        async with self.database.session() as session:
            artifact_repo = ArtifactRepository(session)
            artifact_mgr = ArtifactManager(artifact_repo)

            artifact_out = await artifact_mgr.save(
                ArtifactIn(
                    data=result_data,
                    parent_id=None,
                )
            )

        return artifact_out.id

    async def _execute_python(self, task_id: ULID) -> ULID:
        """Execute Python function and return artifact_id containing results."""
        if self.database is None:
            raise RuntimeError("Database instance required for task execution")

        if self.artifact_manager is None:
            raise RuntimeError("ArtifactManager instance required for task execution")

        # Fetch task and serialize snapshot before execution
        async with self.database.session() as session:
            task_repo = TaskRepository(session)
            task = await task_repo.find_by_id(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")

            # Capture task snapshot
            task_snapshot = {
                "id": str(task.id),
                "command": task.command,
                "task_type": task.task_type,
                "parameters": task.parameters,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }

        # Get function from registry
        try:
            func = TaskRegistry.get(task.command)
        except KeyError:
            raise ValueError(f"Python function '{task.command}' not found in registry")

        # Execute function
        result_data: dict[str, Any]
        try:
            params = task.parameters or {}

            # Handle sync/async functions
            if inspect.iscoroutinefunction(func):
                result = await func(**params)
            else:
                result = await asyncio.to_thread(func, **params)

            result_data = {
                "task": task_snapshot,
                "result": result,
                "error": None,
            }
        except Exception as e:
            result_data = {
                "task": task_snapshot,
                "result": None,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                },
            }

        # Create artifact
        async with self.database.session() as session:
            artifact_repo = ArtifactRepository(session)
            artifact_mgr = ArtifactManager(artifact_repo)
            artifact_out = await artifact_mgr.save(ArtifactIn(data=result_data, parent_id=None))

        return artifact_out.id
