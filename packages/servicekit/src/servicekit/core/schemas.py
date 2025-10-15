"""Core Pydantic schemas for entities, responses, and jobs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar

import ulid
from pydantic import BaseModel, ConfigDict, Field, computed_field

ULID = ulid.ULID
T = TypeVar("T")


# Base entity schemas


class EntityIn(BaseModel):
    """Base input schema for entities with optional ID."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: ULID | None = None


class EntityOut(BaseModel):
    """Base output schema for entities with ID and timestamps."""

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    id: ULID
    created_at: datetime
    updated_at: datetime


# Response schemas


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with items, total count, page number, and computed page count."""

    items: list[T] = Field(description="List of items for the current page")
    total: int = Field(description="Total number of items across all pages", ge=0)
    page: int = Field(description="Current page number (1-indexed)", ge=1)
    size: int = Field(description="Number of items per page", ge=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        """Total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.size - 1) // self.size


class BulkOperationError(BaseModel):
    """Error information for a single item in a bulk operation."""

    id: str = Field(description="Identifier of the item that failed")
    reason: str = Field(description="Human-readable error message")


class BulkOperationResult(BaseModel):
    """Result of bulk operation with counts of succeeded/failed items and error details."""

    total: int = Field(description="Total number of items processed", ge=0)
    succeeded: int = Field(description="Number of items successfully processed", ge=0)
    failed: int = Field(description="Number of items that failed", ge=0)
    errors: list[BulkOperationError] = Field(default_factory=list, description="Details of failed items (if any)")


class ProblemDetail(BaseModel):
    """RFC 9457 Problem Details with URN error type, status, and human-readable messages."""

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type (URN format for chapkit errors)",
    )
    title: str = Field(description="Short, human-readable summary of the problem type")
    status: int = Field(description="HTTP status code", ge=100, le=599)
    detail: str | None = Field(default=None, description="Human-readable explanation specific to this occurrence")
    instance: str | None = Field(default=None, description="URI reference identifying the specific occurrence")
    trace_id: str | None = Field(default=None, description="Optional trace ID for debugging")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "urn:chapkit:error:not-found",
                    "title": "Resource Not Found",
                    "status": 404,
                    "detail": "Config with id 01ABC... not found",
                    "instance": "/api/config/01ABC...",
                }
            ]
        }
    }


# Job schemas


class JobStatus(StrEnum):
    """Status of a scheduled job."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class JobRecord(BaseModel):
    """Complete record of a scheduled job's state and metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: ULID = Field(description="Unique job identifier")
    status: JobStatus = Field(default=JobStatus.pending, description="Current job status")
    submitted_at: datetime | None = Field(default=None, description="When the job was submitted")
    started_at: datetime | None = Field(default=None, description="When the job started running")
    finished_at: datetime | None = Field(default=None, description="When the job finished")
    error: str | None = Field(default=None, description="User-friendly error message if job failed")
    error_traceback: str | None = Field(default=None, description="Full error traceback for debugging")
    artifact_id: ULID | None = Field(default=None, description="ID of artifact created by job (if job returns a ULID)")
