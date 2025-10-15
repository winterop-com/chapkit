"""Custom exceptions with RFC 9457 Problem Details support."""

from __future__ import annotations

from typing import Any


class ErrorType:
    """URN-based error type identifiers for RFC 9457 Problem Details."""

    NOT_FOUND = "urn:chapkit:error:not-found"
    VALIDATION_FAILED = "urn:chapkit:error:validation-failed"
    CONFLICT = "urn:chapkit:error:conflict"
    INVALID_ULID = "urn:chapkit:error:invalid-ulid"
    INTERNAL_ERROR = "urn:chapkit:error:internal"
    UNAUTHORIZED = "urn:chapkit:error:unauthorized"
    FORBIDDEN = "urn:chapkit:error:forbidden"
    BAD_REQUEST = "urn:chapkit:error:bad-request"


class ChapkitException(Exception):
    """Base exception for chapkit with RFC 9457 Problem Details support."""

    def __init__(
        self,
        detail: str,
        *,
        type_uri: str = ErrorType.INTERNAL_ERROR,
        title: str = "Internal Server Error",
        status: int = 500,
        instance: str | None = None,
        **extensions: Any,
    ) -> None:
        super().__init__(detail)
        self.type_uri = type_uri
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance
        self.extensions = extensions


class NotFoundError(ChapkitException):
    """Resource not found exception (404)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.NOT_FOUND,
            title="Resource Not Found",
            status=404,
            instance=instance,
            **extensions,
        )


class ValidationError(ChapkitException):
    """Validation failed exception (400)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.VALIDATION_FAILED,
            title="Validation Failed",
            status=400,
            instance=instance,
            **extensions,
        )


class ConflictError(ChapkitException):
    """Resource conflict exception (409)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.CONFLICT,
            title="Resource Conflict",
            status=409,
            instance=instance,
            **extensions,
        )


class InvalidULIDError(ChapkitException):
    """Invalid ULID format exception (400)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.INVALID_ULID,
            title="Invalid ULID Format",
            status=400,
            instance=instance,
            **extensions,
        )


class BadRequestError(ChapkitException):
    """Bad request exception (400)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.BAD_REQUEST,
            title="Bad Request",
            status=400,
            instance=instance,
            **extensions,
        )


class UnauthorizedError(ChapkitException):
    """Unauthorized exception (401)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.UNAUTHORIZED,
            title="Unauthorized",
            status=401,
            instance=instance,
            **extensions,
        )


class ForbiddenError(ChapkitException):
    """Forbidden exception (403)."""

    def __init__(self, detail: str, *, instance: str | None = None, **extensions: Any) -> None:
        super().__init__(
            detail,
            type_uri=ErrorType.FORBIDDEN,
            title="Forbidden",
            status=403,
            instance=instance,
            **extensions,
        )
