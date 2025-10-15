"""Pagination utilities for API endpoints."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field

from servicekit.core.schemas import PaginatedResponse

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for opt-in pagination (both page and size required)."""

    page: int | None = Field(default=None, ge=1, description="Page number (1-indexed)")
    size: int | None = Field(default=None, ge=1, le=100, description="Number of items per page (max 100)")

    def is_paginated(self) -> bool:
        """Check if both page and size parameters are provided."""
        return self.page is not None and self.size is not None


def create_paginated_response(items: list[T], total: int, page: int, size: int) -> PaginatedResponse[T]:
    """Create paginated response with items and metadata."""
    return PaginatedResponse(items=items, total=total, page=page, size=size)
