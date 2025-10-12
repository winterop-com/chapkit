"""Core framework components - generic interfaces and base classes."""

# ruff: noqa: F401

# Base infrastructure (framework-agnostic)
from .database import Database, SqliteDatabase, SqliteDatabaseBuilder
from .exceptions import (
    BadRequestError,
    ChapkitException,
    ConflictError,
    ErrorType,
    ForbiddenError,
    InvalidULIDError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .logging import add_request_context, clear_request_context, configure_logging, get_logger, reset_request_context
from .manager import BaseManager, LifecycleHooks, Manager
from .models import Base, Entity
from .repository import BaseRepository, Repository
from .scheduler import AIOJobScheduler, JobScheduler
from .schemas import (
    BulkOperationError,
    BulkOperationResult,
    EntityIn,
    EntityOut,
    JobRecord,
    JobStatus,
    PaginatedResponse,
    ProblemDetail,
)
from .types import ULIDType

__all__ = [
    # Base infrastructure
    "Database",
    "SqliteDatabase",
    "SqliteDatabaseBuilder",
    "Repository",
    "BaseRepository",
    "Manager",
    "LifecycleHooks",
    "BaseManager",
    # ORM and types
    "Base",
    "Entity",
    "ULIDType",
    # Schemas
    "EntityIn",
    "EntityOut",
    "PaginatedResponse",
    "BulkOperationResult",
    "BulkOperationError",
    "ProblemDetail",
    "JobRecord",
    "JobStatus",
    # Job scheduling
    "JobScheduler",
    "AIOJobScheduler",
    # Exceptions
    "ErrorType",
    "ChapkitException",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "InvalidULIDError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    # Logging
    "configure_logging",
    "get_logger",
    "add_request_context",
    "clear_request_context",
    "reset_request_context",
]
