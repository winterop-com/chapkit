"""FastAPI middleware for error handling, CORS, and other cross-cutting concerns."""

import time
from typing import Any, Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ulid import ULID

from chapkit.core.exceptions import ChapkitException
from chapkit.core.logging import add_request_context, get_logger, reset_request_context
from chapkit.core.schemas import ProblemDetail

logger = get_logger(__name__)

# Type alias for middleware call_next function
type MiddlewareCallNext = Callable[[Request], Awaitable[Response]]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with unique request IDs and context binding."""

    async def dispatch(self, request: Request, call_next: MiddlewareCallNext) -> Response:
        """Process request with logging and context binding."""
        request_id = str(ULID())
        start_time = time.perf_counter()

        # Bind request context
        add_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Add request_id to request state for access in endpoints
        request.state.request_id = request_id

        logger.info(
            "http.request.start",
            query_params=str(request.url.query) if request.url.query else None,
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "http.request.complete",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request_id to response headers for tracing
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "http.request.error",
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                exc_info=True,
            )
            raise

        finally:
            # Clear request context after response
            reset_request_context()


async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle database errors and return error response."""
    logger.error(
        "database.error",
        error=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred", "error": str(exc)},
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle validation errors and return error response."""
    logger.warning(
        "validation.error",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Validation error", "errors": str(exc)},
    )


async def chapkit_exception_handler(request: Request, exc: ChapkitException) -> JSONResponse:
    """Handle ChapkitException and return RFC 9457 Problem Details."""
    logger.warning(
        "chapkit.error",
        error_type=exc.type_uri,
        status=exc.status,
        detail=exc.detail,
        path=request.url.path,
    )

    problem = ProblemDetail(
        type=exc.type_uri,
        title=exc.title,
        status=exc.status,
        detail=exc.detail,
        instance=exc.instance or str(request.url),
        **exc.extensions,
    )

    return JSONResponse(
        status_code=exc.status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


def add_error_handlers(app: Any) -> None:
    """Add error handlers to FastAPI application."""
    from pydantic import ValidationError
    from sqlalchemy.exc import SQLAlchemyError

    app.add_exception_handler(ChapkitException, chapkit_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)


def add_logging_middleware(app: Any) -> None:
    """Add request logging middleware to FastAPI application."""
    app.add_middleware(RequestLoggingMiddleware)
