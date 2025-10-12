"""FastAPI service demonstrating SSE streaming for long-running job status."""

import asyncio
from typing import Annotated

import ulid
from fastapi import Depends, Request, Response
from pydantic import BaseModel, Field

from chapkit.api import ServiceBuilder, ServiceInfo, build_location_url
from chapkit.core.api import Router
from chapkit.core.api.dependencies import get_scheduler
from chapkit.core.scheduler import JobScheduler

ULID = ulid.ULID


class SlowComputeRequest(BaseModel):
    """Request schema for slow computation with configurable duration."""

    steps: int = Field(default=30, ge=10, le=60, description="Number of steps (seconds)")


class SlowComputeResponse(BaseModel):
    """Response schema with job ID and SSE stream URL."""

    job_id: str = Field(description="Job ID for tracking")
    message: str = Field(description="Human-readable message")
    stream_url: str = Field(description="SSE endpoint URL for real-time status updates")


class SlowComputeResult(BaseModel):
    """Result of completed slow computation."""

    steps_completed: int
    result: int


async def slow_computation(steps: int) -> SlowComputeResult:
    """Simulate slow computation with progress logging."""
    print(f"[TASK] Starting slow computation with {steps} steps...")
    for i in range(steps):
        await asyncio.sleep(1.0)
        print(f"[TASK] Progress: {i+1}/{steps} ({(i+1)*100//steps}%)")
    print("[TASK] Computation complete!")
    return SlowComputeResult(steps_completed=steps, result=42)


class SlowComputeRouter(Router):
    """Router for slow computation jobs with SSE streaming."""

    def _register_routes(self) -> None:
        """Register routes for slow computation job submission."""

        @self.router.post("/slow-compute", response_model=SlowComputeResponse, status_code=202)
        async def submit_slow_computation(
            compute_request: SlowComputeRequest,
            request: Request,
            response: Response,
            scheduler: Annotated[JobScheduler, Depends(get_scheduler)],
        ) -> SlowComputeResponse:
            """Submit a slow computation job (10-60 seconds) and get SSE stream URL."""
            job_id = await scheduler.add_job(slow_computation, compute_request.steps)

            stream_url = f"/api/v1/jobs/{job_id}/$stream"
            response.headers["Location"] = build_location_url(request, f"/api/v1/jobs/{job_id}")

            return SlowComputeResponse(
                job_id=str(job_id),
                message=(
                    f"Job submitted with {compute_request.steps} steps. "
                    f"Stream real-time status updates from: GET {stream_url}"
                ),
                stream_url=stream_url,
            )


info = ServiceInfo(
    display_name="Job Scheduler SSE Streaming Example",
    summary="Long-running jobs with real-time Server-Sent Events status streaming",
    version="1.0.0",
    description=(
        "Demonstrates job scheduler with SSE streaming for real-time status updates. "
        "Submit a slow computation job (30 seconds default) and monitor its progress "
        "using Server-Sent Events instead of polling."
    ),
)

app = (
    ServiceBuilder(info=info)
    .with_health()
    .with_jobs(max_concurrency=5)
    .include_router(SlowComputeRouter.create(prefix="/api/v1", tags=["compute"]))
    .build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("job_scheduler_sse_api:app")
