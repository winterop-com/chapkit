"""API key authentication middleware and utilities."""

import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Set

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from chapkit.core.logging import get_logger
from chapkit.core.schemas import ProblemDetail

logger = get_logger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication via X-API-Key header."""

    def __init__(
        self,
        app: Any,
        *,
        api_keys: Set[str],
        header_name: str = "X-API-Key",
        unauthenticated_paths: Set[str],
    ) -> None:
        """Initialize API key middleware.

        Args:
            app: ASGI application
            api_keys: Set of valid API keys
            header_name: HTTP header name for API key
            unauthenticated_paths: Paths that don't require authentication
        """
        super().__init__(app)
        self.api_keys = api_keys
        self.header_name = header_name
        self.unauthenticated_paths = unauthenticated_paths

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request with API key authentication."""
        # Allow unauthenticated access to specific paths
        if request.url.path in self.unauthenticated_paths:
            return await call_next(request)

        # Extract API key from header
        api_key = request.headers.get(self.header_name)

        if not api_key:
            logger.warning(
                "auth.missing_key",
                path=request.url.path,
                method=request.method,
            )
            problem = ProblemDetail(
                type="urn:chapkit:error:unauthorized",
                title="Unauthorized",
                status=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing authentication header: {self.header_name}",
                instance=str(request.url.path),
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=problem.model_dump(exclude_none=True),
                media_type="application/problem+json",
            )

        # Validate API key
        if api_key not in self.api_keys:
            # Log only prefix for security
            key_prefix = api_key[:7] if len(api_key) >= 7 else "***"
            logger.warning(
                "auth.invalid_key",
                key_prefix=key_prefix,
                path=request.url.path,
                method=request.method,
            )
            problem = ProblemDetail(
                type="urn:chapkit:error:unauthorized",
                title="Unauthorized",
                status=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                instance=str(request.url.path),
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=problem.model_dump(exclude_none=True),
                media_type="application/problem+json",
            )

        # Attach key prefix to request state for logging
        request.state.api_key_prefix = api_key[:7] if len(api_key) >= 7 else "***"

        logger.info(
            "auth.success",
            key_prefix=request.state.api_key_prefix,
            path=request.url.path,
        )

        return await call_next(request)


def load_api_keys_from_env(env_var: str = "CHAPKIT_API_KEYS") -> Set[str]:
    """Load API keys from environment variable (comma-separated).

    Args:
        env_var: Environment variable name

    Returns:
        Set of API keys
    """
    env_value = os.getenv(env_var, "")
    if not env_value:
        return set()
    return {key.strip() for key in env_value.split(",") if key.strip()}


def load_api_keys_from_file(file_path: str | Path) -> Set[str]:
    """Load API keys from file (one key per line).

    Args:
        file_path: Path to file containing API keys

    Returns:
        Set of API keys

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"API key file not found: {file_path}")

    keys = set()
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):  # Skip empty lines and comments
                keys.add(line)

    return keys


def validate_api_key_format(key: str) -> bool:
    """Validate API key format.

    Args:
        key: API key to validate

    Returns:
        True if key format is valid
    """
    # Basic validation: minimum length
    if len(key) < 16:
        return False
    # Optional: Check for prefix pattern like sk_env_random
    # if not key.startswith("sk_"):
    #     return False
    return True
