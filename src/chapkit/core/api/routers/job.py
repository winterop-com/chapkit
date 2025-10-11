"""REST API router for job scheduler (list, get, delete jobs)."""

from __future__ import annotations

from collections.abc import Callable

import ulid
from fastapi import Depends, HTTPException, status
from fastapi.responses import Response

from chapkit.core.api.router import Router
from chapkit.core.scheduler import JobScheduler
from chapkit.core.schemas import JobRecord, JobStatus

ULID = ulid.ULID


class JobRouter(Router):
    """REST API router for job scheduler operations."""

    def __init__(
        self,
        prefix: str,
        tags: list[str],
        scheduler_factory: Callable[[], JobScheduler],
        **kwargs: object,
    ) -> None:
        """Initialize job router with scheduler factory."""
        self.scheduler_factory = scheduler_factory
        super().__init__(prefix=prefix, tags=tags, **kwargs)

    def _register_routes(self) -> None:
        """Register job management endpoints."""
        scheduler_dependency = Depends(self.scheduler_factory)

        @self.router.get("", summary="List all jobs", response_model=list[JobRecord])
        async def get_jobs(
            scheduler: JobScheduler = scheduler_dependency,
            status_filter: JobStatus | None = None,
        ) -> list[JobRecord]:
            jobs = await scheduler.get_all_records()
            if status_filter:
                return [job for job in jobs if job.status == status_filter]
            return jobs

        @self.router.get("/{job_id}", summary="Get job by ID", response_model=JobRecord)
        async def get_job(
            job_id: str,
            scheduler: JobScheduler = scheduler_dependency,
        ) -> JobRecord:
            try:
                ulid_id = ULID.from_str(job_id)
                return await scheduler.get_record(ulid_id)
            except (ValueError, KeyError):
                raise HTTPException(status_code=404, detail="Job not found")

        @self.router.delete("/{job_id}", summary="Cancel and delete job", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_job(
            job_id: str,
            scheduler: JobScheduler = scheduler_dependency,
        ) -> Response:
            try:
                ulid_id = ULID.from_str(job_id)
                await scheduler.delete(ulid_id)
                return Response(status_code=status.HTTP_204_NO_CONTENT)
            except (ValueError, KeyError):
                raise HTTPException(status_code=404, detail="Job not found")
