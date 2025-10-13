"""Custom types for chapkit - SQLAlchemy and Pydantic types."""

from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import PlainSerializer
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


# Pydantic serialization helpers


def _is_json_serializable(value: Any) -> bool:
    """Check if a value is JSON-serializable."""
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError, OverflowError):
        return False


def _create_serialization_metadata(value: Any, *, is_full_object: bool = True) -> dict[str, str]:
    """Create metadata dict for non-serializable values."""
    value_repr = repr(value)
    max_repr_length = 200

    if len(value_repr) > max_repr_length:
        value_repr = value_repr[:max_repr_length] + "..."

    error_msg = (
        "Value is not JSON-serializable. Access the original object from storage if needed."
        if is_full_object
        else "Value is not JSON-serializable."
    )

    return {
        "_type": type(value).__name__,
        "_module": type(value).__module__,
        "_repr": value_repr,
        "_serialization_error": error_msg,
    }


def _serialize_with_metadata(value: Any) -> Any:
    """Serialize value, replacing non-JSON-serializable values with metadata.

    For dicts, each field is serialized individually - serializable values pass through,
    non-serializable values are replaced with metadata dicts containing type information.
    For non-dict values, returns the value if serializable, otherwise metadata.
    """
    # For dicts, serialize each field individually
    if isinstance(value, dict):
        result = {}
        for key, val in value.items():
            if _is_json_serializable(val):
                result[key] = val
            else:
                result[key] = _create_serialization_metadata(val, is_full_object=False)
        return result

    # For non-dict values, serialize or return metadata
    if _is_json_serializable(value):
        return value
    return _create_serialization_metadata(value, is_full_object=True)


SerializableDict = Annotated[
    Any,
    PlainSerializer(_serialize_with_metadata, return_type=Any),
]
"""Pydantic type annotation that serializes values, replacing non-JSON-serializable objects with metadata.

This type is useful for storing flexible data structures that may contain non-serializable objects
like ML models, functions, or custom classes. During serialization, JSON-serializable values pass
through unchanged, while non-serializable values are replaced with metadata dicts containing:
- `_type`: The type name
- `_module`: The module name
- `_repr`: String representation (truncated to 200 chars)
- `_serialization_error`: Error message

Example:
    ```python
    from chapkit.core.types import SerializableDict

    class MySchema(BaseModel):
        data: SerializableDict

    # Serializable values pass through
    obj = MySchema(data={"name": "test", "count": 42})

    # Non-serializable values become metadata
    obj = MySchema(data={"model": LinearRegression(), "version": "1.0"})
    # Serializes to: {"model": {"_type": "LinearRegression", ...}, "version": "1.0"}
    ```
"""
