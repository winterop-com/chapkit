"""Custom SQLAlchemy types for chapkit."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator
from ulid import ULID


class ULIDType(TypeDecorator[ULID]):
    """SQLAlchemy custom type for ULID stored as 26-character strings."""

    impl = String(26)
    cache_ok = True

    def process_bind_param(self, value: ULID | str | None, dialect: Any) -> str | None:
        """Convert ULID to string for database storage."""
        if value is None:
            return None
        if isinstance(value, str):
            return str(ULID.from_str(value))  # Validate and normalize
        return str(value)

    def process_result_value(self, value: str | None, dialect: Any) -> ULID | None:
        """Convert string from database to ULID object."""
        if value is None:
            return None
        return ULID.from_str(value)
