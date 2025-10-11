"""FastAPI service demonstrating job scheduler for async long-running tasks."""

import asyncio
from datetime import datetime
from typing import Annotated

import ulid
from fastapi import Depends, Request, Response
from pydantic import BaseModel, Field

from chapkit.api import ServiceBuilder, ServiceInfo, build_location_url
from chapkit.core.api import Router
from chapkit.core.api.dependencies import get_scheduler
from chapkit.core.exceptions import NotFoundError
from chapkit.core.scheduler import JobScheduler
from chapkit.core.schemas import JobRecord

ULID = ulid.ULID


class ComputeRequest(BaseModel):
    """Request schema for starting a computation with duration."""

    duration: float = Field(description="How long the computation takes (seconds)", ge=0.1, le=60)


class ComputeResponse(BaseModel):
    """Response schema for submitted computation with job tracking info."""

    job_id: str = Field(description="Job ID for tracking")
    message: str = Field(description="Human-readable message")


class ComputeResultResponse(BaseModel):
    """Result of a computation job with status and timestamps."""

    job_id: str
    status: str
    submitted_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: int | None = None
    error: str | None = None


async def long_running_computation(duration: float) -> int:
    """Simulate a long-running computation task that sleeps for given duration."""
    print(f"[TASK] Starting computation for {duration}s...")
    await asyncio.sleep(duration)
    print("[TASK] Computation complete, returning 42")
    return 42


class ComputeRouter(Router):
    """Router for submitting and polling long-running computation jobs."""

    def _register_routes(self) -> None:
        """Register routes for compute job submission and result polling."""

        @self.router.post("/compute", response_model=ComputeResponse, status_code=202)
        async def submit_computation(  # pyright: ignore[reportUnusedFunction]
            compute_request: ComputeRequest,
            request: Request,
            response: Response,
            scheduler: Annotated[JobScheduler, Depends(get_scheduler)],
        ) -> ComputeResponse:
            """Submit a computation job to the scheduler."""
            job_id = await scheduler.add_job(
                long_running_computation,
                compute_request.duration,
            )

            response.headers["Location"] = build_location_url(request, f"/api/v1/jobs/{job_id}")

            return ComputeResponse(
                job_id=str(job_id),
                message=f"Computation job submitted. Poll GET /api/v1/jobs/{job_id} for status.",
            )

        @self.router.get("/compute/{job_id}/result", response_model=ComputeResultResponse)
        async def get_computation_result(  # pyright: ignore[reportUnusedFunction]
            job_id: str,
            scheduler: Annotated[JobScheduler, Depends(get_scheduler)],
        ) -> ComputeResultResponse:
            """Get the result or status of a computation job."""
            ulid_id = ULID.from_str(job_id)
            try:
                record: JobRecord = await scheduler.get_record(ulid_id)
            except KeyError:
                raise NotFoundError(f"Job {job_id} not found")

            result_value = None
            error_value = None

            if record.status == "completed":
                result_value = await scheduler.get_result(ulid_id)
            elif record.status == "failed":
                error_value = record.error

            return ComputeResultResponse(
                job_id=str(record.id),
                status=record.status,
                submitted_at=record.submitted_at,
                started_at=record.started_at,
                finished_at=record.finished_at,
                result=result_value,
                error=error_value,
            )


info = ServiceInfo(
    display_name="Long-Running Computation Service",
    summary="Example service demonstrating job scheduler for async tasks",
    version="1.0.0",
)

app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_jobs(max_concurrency=5)
    .include_router(ComputeRouter.create(prefix="/api/v1", tags=["compute"]))
    .build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("job_scheduler_api:app")
