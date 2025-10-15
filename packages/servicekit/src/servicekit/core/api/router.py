"""Base classes for API routers."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter


class Router(ABC):
    """Base class for FastAPI routers."""

    default_response_model_exclude_none: bool = False

    def __init__(self, prefix: str, tags: Sequence[str], **kwargs: Any) -> None:
        """Initialize router with prefix and tags."""
        self.router = APIRouter(prefix=prefix, tags=list(tags), **kwargs)
        self._register_routes()

    @classmethod
    def create(cls, prefix: str, tags: Sequence[str], **kwargs: Any) -> APIRouter:
        """Create a router instance and return the FastAPI router."""
        return cls(prefix=prefix, tags=tags, **kwargs).router

    @abstractmethod
    def _register_routes(self) -> None:
        """Register routes for this router."""
        ...
