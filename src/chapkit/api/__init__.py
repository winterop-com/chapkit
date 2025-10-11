"""FastAPI routers and related presentation logic."""

from chapkit.core.api import CrudPermissions, CrudRouter, Router
from chapkit.core.api.middleware import (
    add_error_handlers,
    add_logging_middleware,
    database_error_handler,
    validation_error_handler,
)
from chapkit.core.api.routers import HealthRouter, HealthState, HealthStatus, JobRouter, SystemInfo, SystemRouter
from chapkit.core.api.service_builder import ServiceInfo
from chapkit.core.api.utilities import build_location_url, run_app
from chapkit.core.logging import (
    add_request_context,
    clear_request_context,
    configure_logging,
    get_logger,
    reset_request_context,
)
from chapkit.modules.artifact import ArtifactRouter
from chapkit.modules.config import ConfigRouter
from chapkit.modules.task import TaskRouter

from .dependencies import get_artifact_manager, get_config_manager
from .service_builder import AssessedStatus, MLServiceBuilder, MLServiceInfo, ServiceBuilder

__all__ = [
    # Base classes
    "Router",
    "CrudRouter",
    "CrudPermissions",
    # Routers
    "HealthRouter",
    "HealthStatus",
    "HealthState",
    "JobRouter",
    "SystemRouter",
    "SystemInfo",
    "ConfigRouter",
    "ArtifactRouter",
    "TaskRouter",
    # Dependencies
    "get_config_manager",
    "get_artifact_manager",
    # Middleware
    "add_error_handlers",
    "add_logging_middleware",
    "database_error_handler",
    "validation_error_handler",
    # Logging
    "configure_logging",
    "get_logger",
    "add_request_context",
    "clear_request_context",
    "reset_request_context",
    # Builders
    "ServiceBuilder",
    "MLServiceBuilder",
    "ServiceInfo",
    "MLServiceInfo",
    "AssessedStatus",
    # Utilities
    "build_location_url",
    "run_app",
]
