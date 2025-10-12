"""FastAPI framework layer - routers, middleware, utilities."""

from .auth import APIKeyMiddleware, load_api_keys_from_env, load_api_keys_from_file, validate_api_key_format
from .crud import CrudPermissions, CrudRouter
from .dependencies import get_database, get_scheduler, get_session, set_database, set_scheduler
from .middleware import add_error_handlers, add_logging_middleware, database_error_handler, validation_error_handler
from .pagination import PaginationParams, create_paginated_response
from .router import Router
from .routers import HealthRouter, HealthState, HealthStatus, JobRouter, SystemInfo, SystemRouter
from .service_builder import BaseServiceBuilder, ServiceInfo
from .utilities import build_location_url, run_app

__all__ = [
    # Base router classes
    "Router",
    "CrudRouter",
    "CrudPermissions",
    # Service builder
    "BaseServiceBuilder",
    "ServiceInfo",
    # Authentication
    "APIKeyMiddleware",
    "load_api_keys_from_env",
    "load_api_keys_from_file",
    "validate_api_key_format",
    # Dependencies
    "get_database",
    "set_database",
    "get_session",
    "get_scheduler",
    "set_scheduler",
    # Middleware
    "add_error_handlers",
    "add_logging_middleware",
    "database_error_handler",
    "validation_error_handler",
    # Pagination
    "PaginationParams",
    "create_paginated_response",
    # System routers
    "HealthRouter",
    "HealthState",
    "HealthStatus",
    "JobRouter",
    "SystemRouter",
    "SystemInfo",
    # Utilities
    "build_location_url",
    "run_app",
]
