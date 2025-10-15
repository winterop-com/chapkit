"""Server-Sent Events (SSE) utilities for streaming responses."""

from __future__ import annotations

from pydantic import BaseModel

# Standard SSE headers
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # Disable nginx buffering
}


def format_sse_event(data: str) -> bytes:
    """Format data as Server-Sent Events message."""
    return f"data: {data}\n\n".encode("utf-8")


def format_sse_model_event(model: BaseModel, exclude_none: bool = False) -> bytes:
    """Format Pydantic model as Server-Sent Events message."""
    data = model.model_dump_json(exclude_none=exclude_none)
    return format_sse_event(data)
