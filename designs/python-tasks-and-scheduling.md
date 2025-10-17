# Design: Job Scheduling for Tasks

**Status:** Draft
**Date:** 2025-10-17
**Author:** AI Assistant

## Overview

This design extends Chapkit's task execution system with job scheduling capabilities, enabling tasks (both shell and Python) to be scheduled for one-off, interval-based, or cron-based execution.

**Note:** Python task execution (Phase 1) has been **completed and implemented**. This document focuses solely on Phase 2: Job Scheduling.

## Goals

- Support multiple scheduling strategies (once, interval, cron)
- Work with both shell and Python tasks
- Keep implementation simple (in-memory scheduling, no persistence)
- Provide clear migration path to persistent scheduling later

## Non-Goals

- Persistent schedule storage (defer to future iteration)
- Distributed scheduling across multiple nodes

## Background

### Current Task System

Tasks support both shell commands and Python functions (Phase 1 - **IMPLEMENTED**):
- **Shell tasks:** Execute via `asyncio.create_subprocess_shell()`
  - Results: stdout, stderr, exit_code in artifacts
- **Python tasks:** Execute registered functions via TaskRegistry
  - Results: result object or error with traceback in artifacts
- Stateless templates with execution history via artifacts

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

## API Reference

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

## Usage Examples

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

## Testing Strategy

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

## Security Considerations

1. **Registry-only Python execution**: No arbitrary code execution via API
2. **Parameter validation**: Pydantic validation on parameters
3. **Exception isolation**: Python task exceptions don't crash scheduler
4. **Schedule validation**: Cron expressions validated before storage
5. **Resource limits**: Existing job scheduler concurrency controls apply

## Performance Considerations

1. **Scheduler interval**: 60-second check interval balances accuracy and overhead
2. **Lock contention**: Schedule modifications use lock, but execution happens outside lock
3. **Memory**: In-memory storage limited by available RAM (acceptable for MVP)
4. **Cron parsing**: `croniter` performs well for typical use cases

## Migration Path to Persistence

When persistence is needed later:

1. Create `ScheduledTask` ORM model (similar to current `TaskSchedule` Pydantic model)
2. Create `ScheduleRepository` with standard CRUD operations
3. Update `TaskManager._schedules` to load from database on startup
4. Update schedule CRUD methods to persist to database
5. Add database cleanup for completed "once" schedules
6. **No API changes required** - same endpoints, same request/response format

## Future Enhancements

Potential features for later iterations:

1. **Persistence**: Store schedules in database
2. **Schedule history**: Track all executions of a schedule
3. **Retry policies**: Automatic retry on failure
4. **Schedule conflicts**: Detect overlapping executions
5. **Time zones**: Support non-UTC time zones for cron schedules
6. **Schedule templates**: Pre-configured schedule types (daily, weekly, monthly)
7. **Schedule chaining**: Execute task B after task A completes
8. **APScheduler migration**: Switch to battle-tested library

## Open Questions

1. Should schedules be deleted when parent task is deleted?
2. Should we limit max number of schedules per task?
3. Should we expose scheduler worker health/status?
4. Should we support schedule "tags" for bulk enable/disable?

## References

- Current task execution guide: `docs/guides/task-execution.md`
- Job scheduler: `src/chapkit/core/scheduler.py`
- Task module: `src/chapkit/modules/task/`
- Croniter docs: https://github.com/kiorky/croniter

---

**Next Steps:**
1. Review design with stakeholders
2. Get approval on open questions
3. Implement in feature branch
4. Write comprehensive tests
5. Update documentation
6. Create example application
