# Design: Python Task Execution and Job Scheduling

**Status:** Phase 1 Complete, Phase 2 Draft
**Date:** 2025-10-17
**Author:** AI Assistant

## Overview

This design extends Chapkit's task execution system with:
1. **Phase 1 (IMPLEMENTED):** Python function execution with type-based dependency injection
2. **Phase 2 (DRAFT):** Job scheduling for one-off, interval, and cron-based execution

This document captures the complete knowledge of both phases, with emphasis on the implemented Python task execution system.

---

# Phase 1: Python Task Execution (IMPLEMENTED)

## Goals ✅

- Execute registered Python functions as tasks alongside shell commands
- Support both sync and async Python functions
- Provide type-based dependency injection for framework services
- Enable/disable control for tasks
- Validate and auto-disable orphaned Python tasks
- Artifact-based result storage with error handling

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    TaskRegistry                          │
│  - Global function registry (decorator & imperative)     │
│  - register(name): Decorator for functions              │
│  - get(name): Retrieve registered function              │
│  - list_all(): List all registered names                │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     TaskManager                          │
│  - execute_task(task_id): Route to shell or python      │
│  - _execute_command(task_id): Shell execution           │
│  - _execute_python(task_id): Python execution           │
│  - _inject_parameters(): Type-based DI                  │
│  - find_all(enabled=...): Query with filtering          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    TaskRepository                        │
│  - find_all(enabled=...): Filter by enabled status      │
│  - find_by_enabled(bool): Query enabled/disabled        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Task (ORM)                          │
│  - command: str (function name or shell command)        │
│  - task_type: str ("shell" or "python")                 │
│  - parameters: dict | None (JSON for python tasks)      │
│  - enabled: bool (execution control)                    │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

**Added fields to `tasks` table** (via migration `20251010_0927_4d869b5fb06e_initial_schema.py`):

```python
class Task(Entity):
    __tablename__ = "tasks"

    command: Mapped[str]  # Function name (python) or shell command
    task_type: Mapped[str] = mapped_column(default="shell")  # "shell" | "python"
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)  # Enable/disable control
```

## Task Types

### Shell Tasks (Existing)

**Execution:**
- Via `asyncio.create_subprocess_shell()`
- Captures stdout, stderr, exit_code

**Artifact Structure:**
```json
{
  "task": {
    "id": "01TASK...",
    "command": "echo 'Hello World'",
    "created_at": "2025-10-17T...",
    "updated_at": "2025-10-17T..."
  },
  "stdout": "Hello World\n",
  "stderr": "",
  "exit_code": 0
}
```

### Python Tasks (NEW)

**Execution:**
- Via `TaskRegistry.get(function_name)`
- Supports sync and async functions
- Type-based dependency injection
- Parameter validation via function signature

**Artifact Structure (Success):**
```json
{
  "task": {
    "id": "01TASK...",
    "command": "calculate_sum",
    "task_type": "python",
    "parameters": {"a": 10, "b": 32},
    "created_at": "2025-10-17T...",
    "updated_at": "2025-10-17T..."
  },
  "result": {
    "result": 42,
    "operation": "sum"
  },
  "error": null
}
```

**Artifact Structure (Failure):**
```json
{
  "task": {
    "id": "01TASK...",
    "command": "failing_task",
    "task_type": "python",
    "parameters": {"should_fail": true}
  },
  "result": null,
  "error": {
    "type": "ValueError",
    "message": "This task was designed to fail",
    "traceback": "Traceback (most recent call last):\n  ..."
  }
}
```

## TaskRegistry

**Purpose:** Global registry for Python functions to prevent arbitrary code execution

**File:** `src/chapkit/modules/task/registry.py`

### Registration Methods

**1. Decorator (Recommended):**
```python
from chapkit import TaskRegistry

@TaskRegistry.register("my_function")
async def my_function(x: int, y: int) -> dict:
    """Example async function."""
    return {"sum": x + y}
```

**2. Imperative:**
```python
def my_function(x: int) -> dict:
    return {"result": x * 2}

TaskRegistry.register_function("my_function", my_function)
```

### Methods

```python
class TaskRegistry:
    @classmethod
    def register(cls, name: str) -> Callable:
        """Decorator to register a function."""

    @classmethod
    def register_function(cls, name: str, func: Callable) -> None:
        """Imperative registration."""

    @classmethod
    def get(cls, name: str) -> Callable:
        """Retrieve registered function (raises KeyError if not found)."""

    @classmethod
    def list_all(cls) -> list[str]:
        """List all registered function names."""

    @classmethod
    def clear(cls) -> None:
        """Clear registry (useful for testing)."""
```

## Type-Based Dependency Injection

**Feature:** Framework services are automatically injected based on function parameter type hints.

### Injectable Types

```python
INJECTABLE_TYPES = {
    AsyncSession,      # SQLAlchemy async database session
    Database,          # Chapkit Database instance
    ArtifactManager,   # Artifact management service
    JobScheduler,      # Job scheduling service
}
```

### Parameter Sources

1. **User Parameters:** From `task.parameters` (primitives, dicts, lists, pandas DataFrames, etc.)
2. **Framework Injections:** Automatically injected based on type hints

### Examples

**Pure User Parameters:**
```python
@TaskRegistry.register("calculate_sum")
async def calculate_sum(a: int, b: int) -> dict:
    """All params from task.parameters."""
    return {"result": a + b}

# Task: {"command": "calculate_sum", "parameters": {"a": 10, "b": 32}}
```

**Mixed User + Framework:**
```python
@TaskRegistry.register("query_tasks")
async def query_tasks(
    limit: int,              # From task.parameters
    session: AsyncSession,   # Injected by framework
) -> dict:
    """Mix user and injected parameters."""
    from sqlalchemy import select, func
    from chapkit.modules.task.models import Task

    stmt = select(func.count()).select_from(Task)
    result = await session.execute(stmt)
    count = result.scalar() or 0

    return {
        "total": count,
        "limit": limit,
        "using_injection": True
    }

# Task: {"command": "query_tasks", "parameters": {"limit": 100}}
# session is injected automatically based on type hint
```

**Framework-Only (No User Params):**
```python
@TaskRegistry.register("query_task_count")
async def query_task_count(session: AsyncSession) -> dict:
    """No user parameters needed."""
    from sqlalchemy import select, func
    from chapkit.modules.task.models import Task

    stmt = select(func.count()).select_from(Task)
    result = await session.execute(stmt)
    count = result.scalar() or 0

    return {"total_tasks": count}

# Task: {"command": "query_task_count", "parameters": {}}
# Empty parameters - session injected automatically
```

**Optional Injection:**
```python
@TaskRegistry.register("maybe_db")
def maybe_db(
    value: int,
    session: AsyncSession | None = None,  # Optional injection
) -> dict:
    """Optional framework parameter."""
    result = {"value": value}
    if session:
        result["has_session"] = True
    return result

# Works with or without session available
```

### Implementation Details

**Injection Algorithm** (`src/chapkit/modules/task/manager.py:69-127`):

1. Parse function signature with `inspect.signature(func)`
2. Get type hints with `get_type_hints(func)`
3. Build injection map: `{AsyncSession: session_instance, Database: db_instance, ...}`
4. For each parameter:
   - Check if type hint matches injectable type
   - Handle `Optional[Type]` (extract non-None type)
   - If injectable: inject from map
   - If not injectable: must be in `task.parameters` or have default
5. Raise `ValueError` if required non-injectable parameter missing

**Type Checking:**
- Handles both `Type | None` (Python 3.10+ union) and `Union[Type, None]` (typing module)
- Uses `get_origin()` to detect union types
- Extracts non-None types from unions

**Session Management:**
- Creates dedicated session for injection: `database.session()`
- Session enters context before execution
- Session always closes in `finally` block (prevents leaks)
- Artifact saved with separate session (prevents interference)

## Enable/Disable Control

**Feature:** Tasks can be enabled/disabled for execution control without deletion.

### Use Cases

1. **Soft delete:** Disable instead of deleting to preserve history
2. **Maintenance:** Temporarily disable tasks during system maintenance
3. **Orphaned tasks:** Auto-disable tasks with missing Python functions
4. **Gradual rollout:** Create disabled tasks, enable when ready

### Schema

```python
class Task(Entity):
    enabled: Mapped[bool] = mapped_column(default=True)
```

### API Endpoints

**Create with disabled state:**
```bash
POST /api/v1/tasks
{
  "command": "process_data",
  "task_type": "python",
  "parameters": {"input": "test"},
  "enabled": false
}
```

**Filter by enabled status:**
```bash
GET /api/v1/tasks?enabled=true   # Only enabled
GET /api/v1/tasks?enabled=false  # Only disabled
GET /api/v1/tasks                # All tasks
```

**Update enabled status:**
```bash
PUT /api/v1/tasks/{id}
{
  "command": "process_data",
  "enabled": false
}
```

### Execution Validation

Tasks are validated before execution (`src/chapkit/modules/task/manager.py:144-145`):

```python
async def execute_task(self, task_id: ULID) -> ULID:
    task = await self.repo.find_by_id(task_id)
    if not task.enabled:
        raise ValueError(f"Cannot execute disabled task {task_id}")
    # ... continue execution
```

**Error Response:**
```json
{
  "detail": "Cannot execute disabled task 01TASK..."
}
```

## Orphaned Task Validation

**Feature:** Automatically detect and disable Python tasks referencing unregistered functions.

**File:** `src/chapkit/modules/task/validation.py`

### Purpose

Prevent execution failures when:
- Function is removed from code but task still exists in DB
- Service restarts and function registration changes
- Code deployment removes or renames functions

### Implementation

```python
async def validate_and_disable_orphaned_tasks(app: FastAPI) -> int:
    """Validate Python tasks and disable orphaned ones.

    Returns:
        Number of tasks disabled
    """
    database = getattr(app.state, "database", None)
    if database is None:
        return 0

    async with database.session() as session:
        task_repo = TaskRepository(session)
        task_manager = TaskManager(task_repo, ...)

        # Get all tasks
        all_tasks = await task_manager.find_all()

        # Get registered function names
        registered_functions = set(TaskRegistry.list_all())

        # Find orphaned Python tasks
        orphaned_tasks = [
            task for task in all_tasks
            if task.task_type == "python" and task.command not in registered_functions
        ]

        # Disable each orphaned task
        for task in orphaned_tasks:
            logger.warning(
                f"Disabling orphaned task {task.id}: function '{task.command}' not found"
            )
            await task_manager.save(
                TaskIn(id=task.id, ..., enabled=False)
            )

    return len(orphaned_tasks)
```

### Usage in ServiceBuilder

```python
async def validate_tasks_on_startup(app: FastAPI) -> None:
    """Startup hook for validation."""
    await validate_and_disable_orphaned_tasks(app)

app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=3)
    .with_tasks()
    .on_startup(seed_python_tasks)
    .on_startup(validate_tasks_on_startup)  # Auto-disable orphaned tasks
    .build()
)
```

### Logging

**Structured logging with context:**
```python
logger.warning(
    "Found orphaned Python tasks - disabling them",
    extra={
        "count": len(orphaned_tasks),
        "task_ids": [str(task.id) for task in orphaned_tasks],
        "commands": [task.command for task in orphaned_tasks],
    },
)
```

## Read-Only Task API Pattern

**Use Case:** Pre-seed tasks at startup, expose via read-only API for execution

**File:** `examples/readonly_task_api.py`

### Benefits

1. **Version control:** Task definitions in code, not database
2. **Security:** Prevent task creation/modification via API
3. **Consistency:** Same tasks across environments
4. **Production best practice:** Immutable infrastructure

### Implementation

```python
from chapkit.core.api.crud import CrudPermissions

app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=3)
    .with_tasks(
        permissions=CrudPermissions(
            create=False,  # Disable POST /tasks
            read=True,     # Allow GET /tasks, GET /tasks/{id}
            update=False,  # Disable PUT /tasks/{id}
            delete=False,  # Disable DELETE /tasks/{id}
        )
    )
    .on_startup(seed_tasks)  # Pre-seed tasks from code
    .build()
)
```

**Available operations:**
- ✅ `GET /api/v1/tasks` - List tasks
- ✅ `GET /api/v1/tasks/{id}` - Get task
- ✅ `POST /api/v1/tasks/{id}/$execute` - Execute task
- ❌ `POST /api/v1/tasks` - Create task (disabled)
- ❌ `PUT /api/v1/tasks/{id}` - Update task (disabled)
- ❌ `DELETE /api/v1/tasks/{id}` - Delete task (disabled)

## API Reference

### Create Python Task

```bash
POST /api/v1/tasks
Content-Type: application/json

{
  "command": "calculate_sum",
  "task_type": "python",
  "parameters": {"a": 10, "b": 32},
  "enabled": true
}
```

**Response (201):**
```json
{
  "id": "01TASK...",
  "command": "calculate_sum",
  "task_type": "python",
  "parameters": {"a": 10, "b": 32},
  "enabled": true,
  "created_at": "2025-10-17T...",
  "updated_at": "2025-10-17T..."
}
```

### Execute Task

```bash
POST /api/v1/tasks/{id}/$execute
```

**Response (202):**
```json
{
  "job_id": "01JOB...",
  "message": "Task submitted for execution. Job ID: 01JOB..."
}
```

### Get Job Status

```bash
GET /api/v1/jobs/{job_id}
```

**Response (200):**
```json
{
  "id": "01JOB...",
  "status": "completed",
  "artifact_id": "01ARTIFACT...",
  "submitted_at": "2025-10-17T...",
  "started_at": "2025-10-17T...",
  "finished_at": "2025-10-17T..."
}
```

### Get Execution Results

```bash
GET /api/v1/artifacts/{artifact_id}
```

**Response (200):**
```json
{
  "id": "01ARTIFACT...",
  "data": {
    "task": {
      "id": "01TASK...",
      "command": "calculate_sum",
      "task_type": "python",
      "parameters": {"a": 10, "b": 32}
    },
    "result": {
      "result": 42,
      "operation": "sum"
    },
    "error": null
  },
  "created_at": "2025-10-17T...",
  "updated_at": "2025-10-17T..."
}
```

### Filter Tasks by Status

```bash
GET /api/v1/tasks?enabled=true
GET /api/v1/tasks?enabled=false
```

## Testing

**Test Coverage:** 683 tests passing, 6 skipped

### Test Files

1. **`tests/test_task_registry.py`** (151 lines)
   - Decorator registration
   - Imperative registration
   - Duplicate name detection
   - Function retrieval
   - Registry listing
   - Clear functionality

2. **`tests/test_task_injection.py`** (382 lines)
   - AsyncSession injection
   - Database injection
   - ArtifactManager injection
   - Mixed user + injected parameters
   - Optional type handling (`Type | None`)
   - Missing parameter error handling
   - Sync function injection

3. **`tests/test_manager_task.py`** (246 lines added)
   - Python task execution (sync/async)
   - Shell task execution
   - Parameter passing
   - Error handling and artifact structure
   - Enable/disable enforcement
   - Find with enabled filtering

4. **`tests/test_task_repository.py`** (139 lines)
   - `find_all(enabled=True/False/None)`
   - `find_by_enabled(bool)`
   - Query correctness

5. **`tests/test_task_router.py`** (168 lines)
   - Enable/disable via API
   - Query parameter filtering
   - Execution validation

6. **`tests/test_task_validation.py`** (242 lines)
   - Orphaned task detection
   - Auto-disable orphaned tasks
   - Logging verification
   - Registry validation

7. **`tests/test_example_python_task_execution_api.py`** (286 lines)
   - Full integration tests
   - Multiple task types
   - Sync/async function execution
   - Error handling
   - Dependency injection examples
   - Mixed shell and Python tasks

### Test Patterns

**Registry Testing:**
```python
from chapkit import TaskRegistry

def test_register_function():
    TaskRegistry.clear()  # Clean state

    @TaskRegistry.register("test_func")
    def test_func(x: int) -> int:
        return x * 2

    assert "test_func" in TaskRegistry.list_all()
    func = TaskRegistry.get("test_func")
    assert func(5) == 10
```

**Injection Testing:**
```python
async def test_inject_async_session():
    @TaskRegistry.register("needs_session")
    async def needs_session(session: AsyncSession) -> dict:
        assert session is not None
        return {"has_session": True}

    task_manager = TaskManager(repo, scheduler, database, artifact_manager)
    task = await task_manager.save(
        TaskIn(
            command="needs_session",
            task_type="python",
            parameters={},  # Empty - session injected
        )
    )

    job_id = await task_manager.execute_task(task.id)
    # Verify session was injected and task executed
```

**Enable/Disable Testing:**
```python
async def test_cannot_execute_disabled_task():
    task = await task_manager.save(
        TaskIn(command="echo 'test'", enabled=False)
    )

    with pytest.raises(ValueError, match="Cannot execute disabled task"):
        await task_manager.execute_task(task.id)
```

## Documentation

### Guides

1. **`docs/guides/task-execution.md`** (1610 lines)
   - Complete task execution guide
   - Shell and Python task examples
   - Type-based injection documentation
   - Enable/disable patterns
   - Orphaned task validation
   - API reference with examples

2. **`examples/docs/task_python_execution.md`** (543 lines)
   - cURL-based API examples
   - Step-by-step Python task workflow
   - Dependency injection examples
   - Error handling demonstrations

3. **`examples/docs/task_python_execution.postman_collection.json`** (958 lines)
   - Complete Postman collection
   - Pre-configured requests
   - Environment variables
   - Test scripts

4. **`CLAUDE.md`** updates (52 lines added)
   - Task Execution System section
   - Quick reference for TaskRegistry
   - Type-based injection overview
   - Integration with ServiceBuilder

### Example Applications

1. **`examples/task_execution_api.py`** (Original shell example)
   - Simple shell task execution
   - Artifact-based results
   - Basic seeding

2. **`examples/python_task_execution_api.py`** (229 lines)
   - Python function registration
   - Sync/async examples
   - Dependency injection examples
   - Error handling demonstrations
   - Mixed shell and Python tasks
   - Orphaned task validation

3. **`examples/readonly_task_api.py`** (167 lines)
   - Read-only API pattern
   - Pre-seeded tasks
   - CrudPermissions usage
   - Production deployment pattern

## Security Considerations

1. **No Arbitrary Code Execution**
   - Only registered functions can be executed
   - Function names validated against registry
   - No `eval()` or dynamic imports

2. **Parameter Validation**
   - Pydantic validation on `task.parameters`
   - Type hints enforce parameter types
   - Missing required parameters caught before execution

3. **Exception Isolation**
   - Python exceptions captured and stored in artifacts
   - Exceptions don't crash job scheduler
   - Full tracebacks preserved for debugging

4. **Session Management**
   - Dedicated session per execution
   - Always closed in `finally` block
   - No session leaks

5. **Orphaned Task Prevention**
   - Auto-disable tasks with missing functions
   - Prevents execution failures
   - Logged for monitoring

## Performance Considerations

1. **Sync Function Handling**
   - Executed via `asyncio.to_thread()`
   - Doesn't block event loop
   - Suitable for CPU-bound tasks

2. **Async Function Handling**
   - Direct `await` execution
   - Efficient for I/O-bound tasks
   - No thread overhead

3. **Parameter Injection Overhead**
   - Function signature parsed once per execution
   - Type hints retrieved once
   - Minimal overhead (~microseconds)

4. **Registry Lookup**
   - Dictionary-based (O(1) lookup)
   - No parsing or compilation
   - Cached function references

## Migration Guide

### From Shell-Only to Shell + Python

**Before:**
```python
app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=3)
    .with_tasks()  # Only shell tasks
    .build()
)
```

**After:**
```python
# 1. Register Python functions
@TaskRegistry.register("my_function")
async def my_function(x: int) -> dict:
    return {"result": x * 2}

# 2. Add validation hook
async def validate_tasks_on_startup(app: FastAPI) -> None:
    await validate_and_disable_orphaned_tasks(app)

# 3. Same ServiceBuilder, add validation
app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=3)
    .with_tasks()  # Now supports both shell and python
    .on_startup(validate_tasks_on_startup)  # Optional but recommended
    .build()
)
```

**No breaking changes:**
- Existing shell tasks continue to work
- API endpoints unchanged
- Database schema extended (backwards compatible)

## Known Limitations

1. **In-Memory Registry**
   - Registry cleared on restart
   - Must re-register functions on startup
   - No registry persistence

2. **Global Registry**
   - Single global registry per process
   - No namespacing or scoping
   - Function name collisions possible

3. **Parameter Serialization**
   - Parameters must be JSON-serializable
   - Complex objects (pandas DataFrames) stored as dicts
   - No automatic serialization for custom types

4. **No Retry Logic**
   - Failed executions don't retry automatically
   - Must re-execute manually
   - (Can be added in future)

5. **Injection Limitations**
   - Only framework types injectable
   - No custom user-defined injectable types
   - No constructor injection (function parameters only)

## Future Enhancements (Phase 1 Follow-ups)

Potential improvements to Python task execution:

1. **Custom Injectable Types**
   - Allow users to register custom injectable types
   - Service locator pattern
   - `TaskManager.register_injectable(Type, instance)`

2. **Parameter Serialization**
   - Support custom type serializers
   - Automatic pandas DataFrame serialization
   - Protocol for user-defined serializers

3. **Registry Namespacing**
   - Module-scoped registries
   - Avoid name collisions
   - `TaskRegistry("myapp.tasks").register("func")`

4. **Function Versioning**
   - Track function versions
   - Artifact stores which version executed
   - `@TaskRegistry.register("func", version="1.0")`

5. **Retry Policies**
   - Automatic retry on failure
   - Configurable backoff strategies
   - Max retry limits

6. **Result Caching**
   - Cache results based on parameters
   - Avoid re-execution
   - TTL-based invalidation

---

# Phase 2: Job Scheduling (DRAFT)

## Goals

- Support multiple scheduling strategies (once, interval, cron)
- Work with both shell and Python tasks
- Keep implementation simple (in-memory scheduling, no persistence)
- Provide clear migration path to persistent scheduling later

## Non-Goals

- Persistent schedule storage (defer to future iteration)
- Distributed scheduling across multiple nodes

## Background

### Current Job Scheduler

`AIOJobScheduler` provides immediate execution only:
- Submit jobs with `add_job(target, *args, **kwargs)`
- In-memory job tracking (not persisted)
- Concurrency control via semaphore
- Job lifecycle: pending → running → completed/failed/canceled

**Gap:** No ability to schedule tasks for future or recurring execution.

## Design Decisions

### Decision 1: In-Memory Scheduling

**Options Considered:**
1. **In-Memory** (chosen) - Dict-based storage, lost on restart
2. Database-backed - Persist schedules in SQLite
3. APScheduler Integration - Use battle-tested library

**Rationale:**
- Simplest implementation for MVP
- No schema changes required initially
- Easy to migrate to persistence later
- User explicitly requested in-memory for now

**Trade-offs:**
- Schedules lost on service restart
- No clustering/distributed scheduling
- Need to rebuild schedules on startup (if persisted later)

### Decision 2: Scheduling as Task Operation

**Options Considered:**
1. **Operation Endpoint** (chosen) - `POST /tasks/{id}/$schedule`
2. Separate Resource - `POST /schedules` with task_id reference

**Rationale:**
- Consistent with existing `/$execute` pattern
- Simpler API surface (fewer endpoints)
- Scheduling is conceptually an operation on a task

**Trade-offs:**
- Schedule CRUD requires task ID in path
- Listing all schedules requires iterating all tasks

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                     TaskRouter                           │
│  POST /tasks/{id}/$schedule                             │
│  GET /tasks/{id}/$schedules                             │
│  DELETE /tasks/{id}/$schedules/{schedule_id}            │
│  PATCH /tasks/{id}/$schedules/{schedule_id}             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────────────┐
│                   TaskManager                            │
│  ┌──────────────────────────────────────────┐           │
│  │ execute_task(task_id)                    │           │
│  │   (handles both shell and python tasks)  │           │
│  └──────────────────────────────────────────┘           │
│  ┌──────────────────────────────────────────┐           │
│  │ schedule_task(task_id, schedule_config)  │           │
│  │ _scheduler_worker() [background loop]    │           │
│  │ _calculate_next_run(schedule)            │           │
│  └──────────────────────────────────────────┘           │
└─────────────────┬───────────────────────────────────────┘
                  │
                  v
          ┌──────────────────┐
          │  AIOJobScheduler │
          │   add_job()      │
          │   get_status()   │
          └──────────────────┘
```

### Data Flow: Scheduled Task Execution

```
1. User schedules task:
   POST /api/v1/tasks/{id}/$schedule
   {
     "schedule_type": "cron",
     "cron_expression": "0 2 * * *"
   }

2. TaskManager.schedule_task():
   - Validate schedule params
   - Calculate next_run_at
   - Store in _schedules dict
   - Ensure scheduler worker is running

3. Background worker loop (every 60s):
   - Check all enabled schedules
   - If next_run_at <= now:
       - Call execute_task(task_id)
       - Update last_run_at
       - Calculate new next_run_at
       - Disable if schedule_type == "once"

4. Execution flows through normal task execution path
```

## Detailed Design

### 1. Schedule Models

**File:** `src/chapkit/modules/task/schedule.py`

```python
"""Task scheduling models and schemas."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from ulid import ULID


class TaskSchedule(BaseModel):
    """In-memory task schedule representation."""

    id: ULID = Field(description="Unique schedule identifier")
    task_id: ULID = Field(description="ID of task to execute")
    schedule_type: Literal["once", "interval", "cron"] = Field(
        description="Type of schedule"
    )
    run_at: datetime | None = Field(
        default=None,
        description="Specific datetime for 'once' schedules (UTC)",
    )
    interval_seconds: int | None = Field(
        default=None,
        description="Interval in seconds for 'interval' schedules",
    )
    cron_expression: str | None = Field(
        default=None,
        description="Cron expression for 'cron' schedules",
    )
    enabled: bool = Field(
        default=True,
        description="Whether schedule is active",
    )
    next_run_at: datetime = Field(
        description="Next scheduled execution time (UTC)"
    )
    last_run_at: datetime | None = Field(
        default=None,
        description="Last execution time (UTC)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When schedule was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When schedule was last updated",
    )


class ScheduleIn(BaseModel):
    """Input schema for creating task schedules."""

    schedule_type: Literal["once", "interval", "cron"] = Field(
        description="Type of schedule to create"
    )
    run_at: datetime | None = Field(
        default=None,
        description="Specific datetime for 'once' schedules (UTC)",
    )
    interval_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Interval in seconds for 'interval' schedules (minimum 1)",
    )
    cron_expression: str | None = Field(
        default=None,
        description="Cron expression for 'cron' schedules (e.g., '0 2 * * *')",
    )
    enabled: bool = Field(
        default=True,
        description="Whether schedule should be active initially",
    )

    @model_validator(mode="after")
    def validate_schedule_params(self) -> "ScheduleIn":
        """Ensure correct parameters for schedule type."""
        if self.schedule_type == "once":
            if self.run_at is None:
                raise ValueError("run_at required for 'once' schedules")
            if self.run_at <= datetime.now(timezone.utc):
                raise ValueError("run_at must be in the future")
        elif self.schedule_type == "interval":
            if self.interval_seconds is None:
                raise ValueError("interval_seconds required for 'interval' schedules")
        elif self.schedule_type == "cron":
            if self.cron_expression is None:
                raise ValueError("cron_expression required for 'cron' schedules")
            # Validate cron expression
            try:
                from croniter import croniter
                croniter(self.cron_expression, datetime.now(timezone.utc))
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {e}")
        return self


class ScheduleOut(BaseModel):
    """Output schema for task schedules."""

    id: ULID
    task_id: ULID
    schedule_type: Literal["once", "interval", "cron"]
    run_at: datetime | None = None
    interval_seconds: int | None = None
    cron_expression: str | None = None
    enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleUpdateIn(BaseModel):
    """Input schema for updating schedule (enable/disable)."""

    enabled: bool = Field(description="Enable or disable the schedule")
```

### 2. TaskManager Changes

**File:** `src/chapkit/modules/task/manager.py`

Key additions for scheduling:

```python
class TaskManager(BaseManager[Task, TaskIn, TaskOut, ULID]):
    """Manager for Task template entities with artifact-based execution."""

    def __init__(self, ...) -> None:
        # Existing initialization
        ...
        # New: Schedule management
        self._schedules: dict[ULID, TaskSchedule] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._scheduler_lock = asyncio.Lock()

    # Note: execute_task() already exists and handles both shell and python tasks
    # Scheduling methods (NEW)

    async def schedule_task(
        self, task_id: ULID, schedule_in: ScheduleIn
    ) -> ScheduleOut:
        """Create a new schedule for a task."""
        # Verify task exists
        task = await self.repo.find_by_id(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        # Create schedule
        schedule_id = ULID()
        now = datetime.now(timezone.utc)

        schedule = TaskSchedule(
            id=schedule_id,
            task_id=task_id,
            schedule_type=schedule_in.schedule_type,
            run_at=schedule_in.run_at,
            interval_seconds=schedule_in.interval_seconds,
            cron_expression=schedule_in.cron_expression,
            enabled=schedule_in.enabled,
            next_run_at=await self._calculate_next_run_from_input(schedule_in, now),
            last_run_at=None,
            created_at=now,
            updated_at=now,
        )

        async with self._scheduler_lock:
            self._schedules[schedule_id] = schedule
            # Ensure scheduler worker is running
            if self._scheduler_task is None or self._scheduler_task.done():
                self._scheduler_task = asyncio.create_task(self._scheduler_worker())

        return ScheduleOut.model_validate(schedule)

    async def get_schedules_for_task(self, task_id: ULID) -> list[ScheduleOut]:
        """Get all schedules for a specific task."""
        async with self._scheduler_lock:
            schedules = [
                s for s in self._schedules.values() if s.task_id == task_id
            ]
        return [ScheduleOut.model_validate(s) for s in schedules]

    async def update_schedule(
        self, schedule_id: ULID, update: ScheduleUpdateIn
    ) -> ScheduleOut:
        """Update schedule (currently only enable/disable)."""
        async with self._scheduler_lock:
            schedule = self._schedules.get(schedule_id)
            if schedule is None:
                raise KeyError(f"Schedule {schedule_id} not found")

            schedule.enabled = update.enabled
            schedule.updated_at = datetime.now(timezone.utc)

        return ScheduleOut.model_validate(schedule)

    async def delete_schedule(self, schedule_id: ULID) -> None:
        """Delete a schedule."""
        async with self._scheduler_lock:
            if schedule_id not in self._schedules:
                raise KeyError(f"Schedule {schedule_id} not found")
            del self._schedules[schedule_id]

    async def _scheduler_worker(self) -> None:
        """Background worker that checks and triggers scheduled tasks."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                now = datetime.now(timezone.utc)
                schedules_to_run: list[TaskSchedule] = []

                async with self._scheduler_lock:
                    for schedule in self._schedules.values():
                        if schedule.enabled and schedule.next_run_at <= now:
                            schedules_to_run.append(schedule)

                # Execute tasks (outside lock to avoid blocking)
                for schedule in schedules_to_run:
                    try:
                        await self.execute_task(schedule.task_id)

                        # Update schedule
                        async with self._scheduler_lock:
                            schedule.last_run_at = now

                            if schedule.schedule_type == "once":
                                schedule.enabled = False
                            else:
                                schedule.next_run_at = await self._calculate_next_run(schedule)

                            schedule.updated_at = now
                    except Exception as e:
                        # Log error but continue with other schedules
                        print(f"Error executing scheduled task {schedule.task_id}: {e}")

            except Exception as e:
                # Log error but keep worker running
                print(f"Error in scheduler worker: {e}")

    async def _calculate_next_run(self, schedule: TaskSchedule) -> datetime:
        """Calculate next run time based on schedule configuration."""
        now = datetime.now(timezone.utc)

        if schedule.schedule_type == "once":
            # Should not be called for "once" schedules
            return schedule.run_at or now

        elif schedule.schedule_type == "interval":
            # Add interval to last_run or current time
            base_time = schedule.last_run_at or now
            return base_time + timedelta(seconds=schedule.interval_seconds)

        elif schedule.schedule_type == "cron":
            from croniter import croniter
            cron = croniter(schedule.cron_expression, now)
            return cron.get_next(datetime)

        raise ValueError(f"Unknown schedule_type: {schedule.schedule_type}")

    async def _calculate_next_run_from_input(
        self, schedule_in: ScheduleIn, base_time: datetime
    ) -> datetime:
        """Calculate initial next_run_at from schedule input."""
        if schedule_in.schedule_type == "once":
            return schedule_in.run_at

        elif schedule_in.schedule_type == "interval":
            return base_time + timedelta(seconds=schedule_in.interval_seconds)

        elif schedule_in.schedule_type == "cron":
            from croniter import croniter
            cron = croniter(schedule_in.cron_expression, base_time)
            return cron.get_next(datetime)

        raise ValueError(f"Unknown schedule_type: {schedule_in.schedule_type}")
```

### 3. TaskRouter Changes

**File:** `src/chapkit/modules/task/router.py`

Add schedule endpoints:

```python
def _register_routes(self) -> None:
    """Register task CRUD routes and execution/scheduling operations."""
    super()._register_routes()

    manager_factory = self.manager_factory

    # Existing: /$execute endpoint
    ...

    # New: /$schedule endpoint
    async def schedule_task(
        entity_id: str,
        schedule_in: ScheduleIn,
        manager: TaskManager = Depends(manager_factory),
    ) -> ScheduleOut:
        """Schedule a task for execution."""
        task_id = self._parse_ulid(entity_id)
        try:
            return await manager.schedule_task(task_id, schedule_in)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    self.register_entity_operation(
        "schedule",
        schedule_task,
        http_method="POST",
        response_model=ScheduleOut,
        status_code=201,
        summary="Schedule task",
        description="Create a schedule for task execution",
    )

    # New: Get schedules for task
    async def get_task_schedules(
        entity_id: str,
        manager: TaskManager = Depends(manager_factory),
    ) -> list[ScheduleOut]:
        """Get all schedules for a task."""
        task_id = self._parse_ulid(entity_id)
        return await manager.get_schedules_for_task(task_id)

    self.register_entity_operation(
        "schedules",
        get_task_schedules,
        http_method="GET",
        response_model=list[ScheduleOut],
        summary="Get task schedules",
        description="List all schedules for this task",
    )

    # New: Delete schedule
    async def delete_task_schedule(
        entity_id: str,
        schedule_id: str,
        manager: TaskManager = Depends(manager_factory),
    ) -> None:
        """Delete a task schedule."""
        try:
            schedule_ulid = ULID.from_str(schedule_id)
            await manager.delete_schedule(schedule_ulid)
        except (ValueError, KeyError) as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Custom route pattern for schedule operations
    @self.router.delete(
        "/{entity_id}/$schedules/{schedule_id}",
        status_code=204,
        summary="Delete schedule",
        tags=self.tags,
    )
    async def delete_schedule_route(
        entity_id: str,
        schedule_id: str,
        manager: TaskManager = Depends(manager_factory),
    ):
        await delete_task_schedule(entity_id, schedule_id, manager)

    # New: Update schedule (enable/disable)
    @self.router.patch(
        "/{entity_id}/$schedules/{schedule_id}",
        response_model=ScheduleOut,
        summary="Update schedule",
        tags=self.tags,
    )
    async def update_schedule_route(
        entity_id: str,
        schedule_id: str,
        update: ScheduleUpdateIn,
        manager: TaskManager = Depends(manager_factory),
    ):
        try:
            schedule_ulid = ULID.from_str(schedule_id)
            return await manager.update_schedule(schedule_ulid, update)
        except (ValueError, KeyError) as e:
            raise HTTPException(status_code=404, detail=str(e))
```

## API Reference (Phase 2)

### Scheduling Endpoints

#### POST /api/v1/tasks/{task_id}/$schedule
Create a schedule for a task.

**Request (one-off):**
```json
{
  "schedule_type": "once",
  "run_at": "2025-10-20T14:00:00Z",
  "enabled": true
}
```

**Request (interval):**
```json
{
  "schedule_type": "interval",
  "interval_seconds": 3600,
  "enabled": true
}
```

**Request (cron):**
```json
{
  "schedule_type": "cron",
  "cron_expression": "0 2 * * *",
  "enabled": true
}
```

**Response (201):**
```json
{
  "id": "01SCHEDULE...",
  "task_id": "01TASK...",
  "schedule_type": "cron",
  "cron_expression": "0 2 * * *",
  "enabled": true,
  "next_run_at": "2025-10-18T02:00:00Z",
  "last_run_at": null,
  "created_at": "2025-10-17T10:00:00Z",
  "updated_at": "2025-10-17T10:00:00Z"
}
```

#### GET /api/v1/tasks/{task_id}/$schedules
List all schedules for a task.

**Response (200):**
```json
[
  {
    "id": "01SCHEDULE...",
    "task_id": "01TASK...",
    "schedule_type": "interval",
    "interval_seconds": 3600,
    "enabled": true,
    "next_run_at": "2025-10-17T11:00:00Z",
    "last_run_at": "2025-10-17T10:00:00Z",
    "created_at": "2025-10-17T09:00:00Z",
    "updated_at": "2025-10-17T10:00:00Z"
  }
]
```

#### PATCH /api/v1/tasks/{task_id}/$schedules/{schedule_id}
Update a schedule (enable/disable).

**Request:**
```json
{
  "enabled": false
}
```

**Response (200):**
```json
{
  "id": "01SCHEDULE...",
  "enabled": false,
  ...
}
```

#### DELETE /api/v1/tasks/{task_id}/$schedules/{schedule_id}
Delete a schedule.

**Response (204):** No content

## Usage Examples (Phase 2)

### Example 1: Schedule Task with Cron

```bash
# Create task (shell or python)
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "backup_database", "task_type": "python"}' | jq -r '.id')

# Schedule to run daily at 2 AM
SCHEDULE_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$schedule \
  -d '{
    "schedule_type": "cron",
    "cron_expression": "0 2 * * *"
  }' | jq -r '.id')

# List all schedules for task
curl http://localhost:8000/api/v1/tasks/$TASK_ID/\$schedules

# Disable schedule temporarily
curl -X PATCH http://localhost:8000/api/v1/tasks/$TASK_ID/\$schedules/$SCHEDULE_ID \
  -d '{"enabled": false}'

# Re-enable
curl -X PATCH http://localhost:8000/api/v1/tasks/$TASK_ID/\$schedules/$SCHEDULE_ID \
  -d '{"enabled": true}'

# Delete schedule
curl -X DELETE http://localhost:8000/api/v1/tasks/$TASK_ID/\$schedules/$SCHEDULE_ID
```

### Example 2: Interval-Based Monitoring

```python
# Register monitoring task
@TaskRegistry.register("health_check")
async def health_check() -> dict:
    """Check system health."""
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

```bash
# Create monitoring task
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "health_check", "task_type": "python"}' | jq -r '.id')

# Schedule to run every 5 minutes
curl -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$schedule \
  -d '{
    "schedule_type": "interval",
    "interval_seconds": 300
  }'

# Monitor execution history via jobs/artifacts
curl http://localhost:8000/api/v1/jobs?page=1&size=20
```

## Testing Strategy (Phase 2)

### Unit Tests

**test_schedule_validation.py:**
- Validate "once" schedule requires run_at
- Validate "interval" schedule requires interval_seconds
- Validate "cron" schedule requires valid cron_expression
- Reject invalid cron expressions
- Reject past timestamps for "once" schedules

**test_next_run_calculation.py:**
- Calculate next run for "once" schedules
- Calculate next run for "interval" schedules
- Calculate next run for "cron" schedules
- Handle edge cases (month boundaries, DST, leap years for cron)

### Integration Tests

**test_task_scheduling.py:**
- Create schedule via API
- List schedules for task
- Update schedule (enable/disable)
- Delete schedule
- Verify scheduled execution occurs
- Verify "once" schedule disables after execution
- Verify "interval" schedule calculates next run correctly

**test_scheduler_worker.py:**
- Worker executes due schedules
- Worker skips disabled schedules
- Worker continues after task failure
- Worker updates last_run_at and next_run_at
- Multiple schedules for same task execute correctly

## Migration Path to Persistence

When persistence is needed later:

1. Create `ScheduledTask` ORM model (similar to current `TaskSchedule` Pydantic model)
2. Create `ScheduleRepository` with standard CRUD operations
3. Update `TaskManager._schedules` to load from database on startup
4. Update schedule CRUD methods to persist to database
5. Add database cleanup for completed "once" schedules
6. **No API changes required** - same endpoints, same request/response format

## Open Questions (Phase 2)

1. Should schedules be deleted when parent task is deleted?
2. Should we limit max number of schedules per task?
3. Should we expose scheduler worker health/status?
4. Should we support schedule "tags" for bulk enable/disable?

## References

- Current task execution guide: `docs/guides/task-execution.md`
- Python task execution examples: `examples/python_task_execution_api.py`
- Job scheduler: `src/chapkit/core/scheduler.py`
- Task module: `src/chapkit/modules/task/`
- Croniter docs: https://github.com/kiorky/croniter

---

## Summary

**Phase 1 (IMPLEMENTED):** Python task execution with type-based dependency injection is complete with comprehensive testing (683 tests passing) and documentation.

**Phase 2 (DRAFT):** Job scheduling design is ready for implementation when needed.

Both phases integrate seamlessly with existing chapkit architecture and maintain backwards compatibility with shell task execution.
