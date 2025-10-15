"""Task CRUD router with execution operation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field

from servicekit.core.api.crud import CrudPermissions, CrudRouter

from .manager import TaskManager
from .schemas import TaskIn, TaskOut


class TaskExecuteResponse(BaseModel):
    """Response schema for task execution."""

    job_id: str = Field(description="ID of the scheduler job")
    message: str = Field(description="Human-readable message")


class TaskRouter(CrudRouter[TaskIn, TaskOut]):
    """CRUD router for Task entities with execution operation."""

    def __init__(
        self,
        prefix: str,
        tags: Sequence[str],
        manager_factory: Any,
        entity_in_type: type[TaskIn],
        entity_out_type: type[TaskOut],
        permissions: CrudPermissions | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize task router with entity types and manager factory."""
        super().__init__(
            prefix=prefix,
            tags=list(tags),
            entity_in_type=entity_in_type,
            entity_out_type=entity_out_type,
            manager_factory=manager_factory,
            permissions=permissions,
            **kwargs,
        )

    def _register_routes(self) -> None:
        """Register task CRUD routes and execution operation."""
        super()._register_routes()

        manager_factory = self.manager_factory

        async def execute_task(
            entity_id: str,
            manager: TaskManager = Depends(manager_factory),
        ) -> TaskExecuteResponse:
            """Execute a task asynchronously via the job scheduler."""
            task_id = self._parse_ulid(entity_id)

            try:
                job_id = await manager.execute_task(task_id)
                return TaskExecuteResponse(
                    job_id=str(job_id),
                    message=f"Task submitted for execution. Job ID: {job_id}",
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(e),
                )

        self.register_entity_operation(
            "execute",
            execute_task,
            http_method="POST",
            response_model=TaskExecuteResponse,
            status_code=status.HTTP_202_ACCEPTED,
            summary="Execute task",
            description="Submit the task to the scheduler for execution",
        )
