"""FastAPI service demonstrating Python task execution with TaskRegistry."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from fastapi import FastAPI
from ulid import ULID

from chapkit import (
    ArtifactHierarchy,
    TaskIn,
    TaskManager,
    TaskRegistry,
    TaskRepository,
    validate_and_disable_orphaned_tasks,
)
from chapkit.api import ServiceBuilder, ServiceInfo
from chapkit.core import Database


# Register Python task functions
@TaskRegistry.register("calculate_sum")
async def calculate_sum(a: int, b: int) -> dict:
    """Calculate sum of two numbers asynchronously."""
    await asyncio.sleep(0.1)  # Simulate async work
    return {"result": a + b, "operation": "sum"}


@TaskRegistry.register("process_data")
def process_data(input_text: str, uppercase: bool = False) -> dict:
    """Process text data synchronously."""
    result = input_text.upper() if uppercase else input_text.lower()
    return {
        "original": input_text,
        "processed": result,
        "length": len(result),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@TaskRegistry.register("slow_computation")
def slow_computation(seconds: int = 2) -> dict:
    """Simulate slow computation (sync function)."""
    time.sleep(seconds)
    return {"completed": True, "duration_seconds": seconds}


@TaskRegistry.register("failing_task")
async def failing_task(should_fail: bool = True) -> dict:
    """Task that demonstrates error handling."""
    if should_fail:
        raise ValueError("This task was designed to fail")
    return {"success": True}


async def seed_python_tasks(app: FastAPI) -> None:
    """Seed example Python task templates with stable ULIDs."""
    database: Database | None = getattr(app.state, "database", None)
    if database is None:
        return

    async with database.session() as session:
        task_repo = TaskRepository(session)
        task_manager = TaskManager(task_repo, scheduler=None, database=None, artifact_manager=None)

        # Check if tasks already exist
        existing_tasks = await task_manager.find_all()
        if len(existing_tasks) > 0:
            return  # Skip seeding if tasks already exist

        # Example 1: Async Python function with parameters
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH1"),
                command="calculate_sum",
                task_type="python",
                parameters={"a": 10, "b": 32},
            )
        )

        # Example 2: Sync Python function with parameters
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH2"),
                command="process_data",
                task_type="python",
                parameters={"input_text": "Hello World", "uppercase": True},
            )
        )

        # Example 3: Slow computation
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH3"),
                command="slow_computation",
                task_type="python",
                parameters={"seconds": 1},
            )
        )

        # Example 4: Error handling demonstration
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH4"),
                command="failing_task",
                task_type="python",
                parameters={"should_fail": True},
                enabled=True,
            )
        )

        # Example 5: Traditional shell task (for comparison)
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH5"),
                command='echo "This is a shell task"',
                task_type="shell",
                enabled=True,
            )
        )

        # Example 6: Disabled task (won't execute)
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH6"),
                command="process_data",
                task_type="python",
                parameters={"input_text": "Disabled", "uppercase": False},
                enabled=False,
            )
        )

        # Example 7: Orphaned task (function not registered - will be auto-disabled)
        await task_manager.save(
            TaskIn(
                id=ULID.from_str("01JCSEED0000000000000PYTH7"),
                command="nonexistent_function",
                task_type="python",
                parameters={},
                enabled=True,
            )
        )


info = ServiceInfo(
    display_name="Python Task Execution Service",
    summary="Example service demonstrating Python function execution via TaskRegistry",
    version="1.0.0",
    description="""
    This service demonstrates chapkit's Python task execution capabilities.

    Features:
    - Register Python functions with @TaskRegistry.register()
    - Support both sync and async functions
    - Pass parameters as dict to functions
    - Capture results or exceptions in artifacts
    - Mix Python and shell tasks in the same service
    - Enable/disable tasks for execution control
    - Automatic validation and disabling of orphaned tasks
    """,
)

# Simple hierarchy for task execution artifacts
TASK_HIERARCHY = ArtifactHierarchy(
    name="task_executions",
    level_labels={0: "execution"},
)


async def validate_tasks_on_startup(app: FastAPI) -> None:
    """Wrapper for validation that discards return value."""
    await validate_and_disable_orphaned_tasks(app)


app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_artifacts(hierarchy=TASK_HIERARCHY)  # Required for task execution results
    .with_jobs(max_concurrency=3)  # Limit concurrent task execution
    .with_tasks()
    .on_startup(seed_python_tasks)
    .on_startup(validate_tasks_on_startup)  # Auto-disable orphaned Python tasks
    .build()
)

if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("python_task_execution_api:app")
