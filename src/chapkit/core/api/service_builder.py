"""Base service builder for FastAPI applications without module dependencies."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncContextManager, AsyncIterator, Awaitable, Callable, Dict, List, Self

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from chapkit.core import Database, SqliteDatabase
from chapkit.core.logging import configure_logging, get_logger

from .app import App, AppLoader
from .auth import APIKeyMiddleware, load_api_keys_from_env, load_api_keys_from_file
from .dependencies import get_database, get_scheduler, set_database, set_scheduler
from .middleware import add_error_handlers, add_logging_middleware
from .routers import HealthRouter, JobRouter, MetricsRouter, SystemRouter
from .routers.health import HealthCheck, HealthState

logger = get_logger(__name__)

# Type aliases for service builder
type LifecycleHook = Callable[[FastAPI], Awaitable[None]]
type DependencyOverride = Callable[..., object]
type LifespanFactory = Callable[[FastAPI], AsyncContextManager[None]]


@dataclass(frozen=True)
class _HealthOptions:
    """Configuration for health check endpoints."""

    prefix: str
    tags: List[str]
    checks: dict[str, HealthCheck]


@dataclass(frozen=True)
class _SystemOptions:
    """Configuration for system info endpoints."""

    prefix: str
    tags: List[str]


@dataclass(frozen=True)
class _JobOptions:
    """Configuration for job scheduler endpoints."""

    prefix: str
    tags: List[str]
    max_concurrency: int | None


@dataclass(frozen=True)
class _AuthOptions:
    """Configuration for API key authentication."""

    api_keys: set[str]
    header_name: str
    unauthenticated_paths: set[str]
    source: str


@dataclass(frozen=True)
class _MonitoringOptions:
    """Configuration for OpenTelemetry monitoring."""

    prefix: str
    tags: List[str]
    service_name: str | None
    enable_traces: bool


class ServiceInfo(BaseModel):
    """Service metadata for FastAPI application."""

    display_name: str
    version: str = "1.0.0"
    summary: str | None = None
    description: str | None = None
    contact: dict[str, str] | None = None
    license_info: dict[str, str] | None = None

    model_config = ConfigDict(extra="forbid")


class BaseServiceBuilder:
    """Base service builder providing core FastAPI functionality without module dependencies."""

    def __init__(
        self,
        *,
        info: ServiceInfo,
        database_url: str = "sqlite+aiosqlite:///:memory:",
        include_error_handlers: bool = True,
        include_logging: bool = False,
    ) -> None:
        """Initialize base service builder with core options."""
        if info.description is None and info.summary is not None:
            # Preserve summary as description for FastAPI metadata if description missing
            self.info = info.model_copy(update={"description": info.summary})
        else:
            self.info = info
        self._title = self.info.display_name
        self._app_description = self.info.summary or self.info.description or ""
        self._version = self.info.version
        self._database_url = database_url
        self._database_instance: Database | None = None
        self._pool_size: int = 5
        self._max_overflow: int = 10
        self._pool_recycle: int = 3600
        self._pool_pre_ping: bool = True
        self._include_error_handlers = include_error_handlers
        self._include_logging = include_logging
        self._health_options: _HealthOptions | None = None
        self._system_options: _SystemOptions | None = None
        self._job_options: _JobOptions | None = None
        self._auth_options: _AuthOptions | None = None
        self._monitoring_options: _MonitoringOptions | None = None
        self._app_configs: List[App] = []
        self._custom_routers: List[APIRouter] = []
        self._dependency_overrides: Dict[DependencyOverride, DependencyOverride] = {}
        self._startup_hooks: List[LifecycleHook] = []
        self._shutdown_hooks: List[LifecycleHook] = []

    # --------------------------------------------------------------------- Fluent configuration

    def with_database(
        self,
        url_or_instance: str | Database | None = None,
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
    ) -> Self:
        """Configure database with URL string, Database instance, or default in-memory SQLite."""
        if isinstance(url_or_instance, Database):
            # Pre-configured instance provided
            self._database_instance = url_or_instance
            return self  # Skip pool configuration for instances
        elif isinstance(url_or_instance, str):
            # String URL provided
            self._database_url = url_or_instance
        elif url_or_instance is None:
            # Default: in-memory SQLite
            self._database_url = "sqlite+aiosqlite:///:memory:"
        else:
            raise TypeError(
                f"Expected str, Database, or None, got {type(url_or_instance).__name__}. "
                "Use .with_database() for default, .with_database('url') for custom URL, "
                "or .with_database(db_instance) for pre-configured database."
            )

        # Configure pool settings (only applies to URL-based databases)
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_recycle = pool_recycle
        self._pool_pre_ping = pool_pre_ping
        return self

    def with_landing_page(self) -> Self:
        """Enable landing page at root path.

        This is internally implemented as mounting the built-in landing page app at "/".
        Users can override this by calling .with_app(..., prefix="/") after this method.
        """
        return self.with_app(("chapkit.core.api", "apps/landing"))

    def with_logging(self, enabled: bool = True) -> Self:
        """Enable structured logging with request tracing."""
        self._include_logging = enabled
        return self

    def with_health(
        self,
        *,
        prefix: str = "/health",
        tags: List[str] | None = None,
        checks: dict[str, HealthCheck] | None = None,
        include_database_check: bool = True,
    ) -> Self:
        """Add health check endpoint with optional custom checks."""
        health_checks = checks or {}

        if include_database_check:
            health_checks["database"] = self._create_database_health_check()

        self._health_options = _HealthOptions(
            prefix=prefix,
            tags=list(tags) if tags is not None else ["Observability"],
            checks=health_checks,
        )
        return self

    def with_system(
        self,
        *,
        prefix: str = "/api/v1/system",
        tags: List[str] | None = None,
    ) -> Self:
        """Add system info endpoint."""
        self._system_options = _SystemOptions(
            prefix=prefix,
            tags=list(tags) if tags is not None else ["Service"],
        )
        return self

    def with_jobs(
        self,
        *,
        prefix: str = "/api/v1/jobs",
        tags: List[str] | None = None,
        max_concurrency: int | None = None,
    ) -> Self:
        """Add job scheduler endpoints."""
        self._job_options = _JobOptions(
            prefix=prefix,
            tags=list(tags) if tags is not None else ["Jobs"],
            max_concurrency=max_concurrency,
        )
        return self

    def with_auth(
        self,
        *,
        api_keys: List[str] | None = None,
        api_key_file: str | None = None,
        env_var: str = "CHAPKIT_API_KEYS",
        header_name: str = "X-API-Key",
        unauthenticated_paths: List[str] | None = None,
    ) -> Self:
        """Enable API key authentication."""
        keys: set[str] = set()
        auth_source: str = ""  # Track source for later logging

        # Priority 1: Direct list (examples/dev)
        if api_keys is not None:
            keys = set(api_keys)
            auth_source = "direct_keys"

        # Priority 2: File (Docker secrets)
        elif api_key_file is not None:
            keys = load_api_keys_from_file(api_key_file)
            auth_source = f"file:{api_key_file}"

        # Priority 3: Environment variable (default)
        else:
            keys = load_api_keys_from_env(env_var)
            if keys:
                auth_source = f"env:{env_var}"
            else:
                auth_source = f"env:{env_var}:empty"

        if not keys:
            raise ValueError("No API keys configured. Provide api_keys, api_key_file, or set environment variable.")

        # Default unauthenticated paths
        default_unauth = {"/docs", "/redoc", "/openapi.json", "/health", "/"}
        unauth_set = set(unauthenticated_paths) if unauthenticated_paths else default_unauth

        self._auth_options = _AuthOptions(
            api_keys=keys,
            header_name=header_name,
            unauthenticated_paths=unauth_set,
            source=auth_source,
        )
        return self

    def with_monitoring(
        self,
        *,
        prefix: str = "/metrics",
        tags: List[str] | None = None,
        service_name: str | None = None,
        enable_traces: bool = False,
    ) -> Self:
        """Enable OpenTelemetry monitoring with Prometheus endpoint and auto-instrumentation."""
        self._monitoring_options = _MonitoringOptions(
            prefix=prefix,
            tags=list(tags) if tags is not None else ["Observability"],
            service_name=service_name,
            enable_traces=enable_traces,
        )
        return self

    def with_app(self, path: str | Path | tuple[str, str], prefix: str | None = None) -> Self:
        """Register static app from filesystem path or package resource tuple."""
        app = AppLoader.load_app(path, prefix=prefix)
        self._app_configs.append(app)
        return self

    def with_apps(self, path: str | Path | tuple[str, str]) -> Self:
        """Auto-discover and register all apps in directory."""
        apps = AppLoader.discover_apps(path)
        self._app_configs.extend(apps)
        return self

    def include_router(self, router: APIRouter) -> Self:
        """Include a custom router."""
        self._custom_routers.append(router)
        return self

    def override_dependency(self, dependency: DependencyOverride, override: DependencyOverride) -> Self:
        """Override a dependency for testing or customization."""
        self._dependency_overrides[dependency] = override
        return self

    def on_startup(self, hook: LifecycleHook) -> Self:
        """Register a startup hook."""
        self._startup_hooks.append(hook)
        return self

    def on_shutdown(self, hook: LifecycleHook) -> Self:
        """Register a shutdown hook."""
        self._shutdown_hooks.append(hook)
        return self

    # --------------------------------------------------------------------- Build mechanics

    def build(self) -> FastAPI:
        """Build and configure the FastAPI application."""
        self._validate_configuration()
        self._validate_module_configuration()  # Extension point for subclasses

        lifespan = self._build_lifespan()
        app = FastAPI(
            title=self._title,
            description=self._app_description,
            version=self._version,
            lifespan=lifespan,
        )
        app.state.database_url = self._database_url

        # Override schema generation to clean up generic type names
        app.openapi = self._create_openapi_customizer(app)  # type: ignore[method-assign]

        if self._include_error_handlers:
            add_error_handlers(app)

        if self._include_logging:
            add_logging_middleware(app)

        if self._auth_options:
            app.add_middleware(
                APIKeyMiddleware,
                api_keys=self._auth_options.api_keys,
                header_name=self._auth_options.header_name,
                unauthenticated_paths=self._auth_options.unauthenticated_paths,
            )
            # Store auth_source for logging during startup
            app.state.auth_source = self._auth_options.source
            app.state.auth_key_count = len(self._auth_options.api_keys)

        if self._health_options:
            health_router = HealthRouter.create(
                prefix=self._health_options.prefix,
                tags=self._health_options.tags,
                checks=self._health_options.checks,
            )
            app.include_router(health_router)

        if self._system_options:
            system_router = SystemRouter.create(
                prefix=self._system_options.prefix,
                tags=self._system_options.tags,
            )
            app.include_router(system_router)

        if self._job_options:
            job_router = JobRouter.create(
                prefix=self._job_options.prefix,
                tags=self._job_options.tags,
                scheduler_factory=get_scheduler,
            )
            app.include_router(job_router)

        if self._monitoring_options:
            from .monitoring import setup_monitoring

            metric_reader = setup_monitoring(
                app,
                service_name=self._monitoring_options.service_name,
                enable_traces=self._monitoring_options.enable_traces,
            )
            metrics_router = MetricsRouter.create(
                prefix=self._monitoring_options.prefix,
                tags=self._monitoring_options.tags,
                metric_reader=metric_reader,
            )
            app.include_router(metrics_router)

        # Extension point for module-specific routers
        self._register_module_routers(app)

        for router in self._custom_routers:
            app.include_router(router)

        # Install route endpoints BEFORE mounting apps (routes take precedence over mounts)
        self._install_info_endpoint(app, info=self.info)

        # Mount apps AFTER all routes (apps act as catch-all for unmatched paths)
        if self._app_configs:
            from fastapi.staticfiles import StaticFiles

            for app_config in self._app_configs:
                static_files = StaticFiles(directory=str(app_config.directory), html=True)
                app.mount(app_config.prefix, static_files, name=f"app_{app_config.manifest.name}")
                logger.info(
                    "app.mounted",
                    name=app_config.manifest.name,
                    prefix=app_config.prefix,
                    directory=str(app_config.directory),
                    is_package=app_config.is_package,
                )

        for dependency, override in self._dependency_overrides.items():
            app.dependency_overrides[dependency] = override

        return app

    # --------------------------------------------------------------------- Extension points

    def _validate_module_configuration(self) -> None:
        """Extension point for module-specific validation (override in subclasses)."""
        pass

    def _register_module_routers(self, app: FastAPI) -> None:
        """Extension point for registering module-specific routers (override in subclasses)."""
        pass

    # --------------------------------------------------------------------- Core helpers

    def _validate_configuration(self) -> None:
        """Validate core configuration."""
        # Validate health check names don't contain invalid characters
        if self._health_options:
            for name in self._health_options.checks.keys():
                if not name.replace("_", "").replace("-", "").isalnum():
                    raise ValueError(
                        f"Health check name '{name}' contains invalid characters. "
                        "Only alphanumeric characters, underscores, and hyphens are allowed."
                    )

        # Validate app configurations
        if self._app_configs:
            # Deduplicate apps with same prefix (last one wins)
            # This allows overriding apps, especially useful for root prefix "/"
            seen_prefixes: dict[str, int] = {}  # prefix -> last index
            for i, app in enumerate(self._app_configs):
                if app.prefix in seen_prefixes:
                    # Log warning about override
                    prev_idx = seen_prefixes[app.prefix]
                    prev_app = self._app_configs[prev_idx]
                    logger.warning(
                        "app.prefix.override",
                        prefix=app.prefix,
                        replaced_app=prev_app.manifest.name,
                        new_app=app.manifest.name,
                    )
                seen_prefixes[app.prefix] = i

            # Keep only the last app for each prefix
            self._app_configs = [self._app_configs[i] for i in sorted(set(seen_prefixes.values()))]

            # Validate that non-root prefixes don't have duplicates (shouldn't happen after dedup, but safety check)
            prefixes = [app.prefix for app in self._app_configs]
            if len(prefixes) != len(set(prefixes)):
                raise ValueError("Internal error: duplicate prefixes after deduplication")

    def _build_lifespan(self) -> LifespanFactory:
        """Build lifespan context manager for app startup/shutdown."""
        database_url = self._database_url
        database_instance = self._database_instance
        pool_size = self._pool_size
        max_overflow = self._max_overflow
        pool_recycle = self._pool_recycle
        pool_pre_ping = self._pool_pre_ping
        job_options = self._job_options
        include_logging = self._include_logging
        startup_hooks = list(self._startup_hooks)
        shutdown_hooks = list(self._shutdown_hooks)

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncIterator[None]:
            # Configure logging if enabled
            if include_logging:
                configure_logging()

            # Use injected database or create new one from URL
            if database_instance is not None:
                database = database_instance
                should_manage_lifecycle = False
            else:
                # Create appropriate database type based on URL
                if "sqlite" in database_url.lower():
                    database = SqliteDatabase(
                        database_url,
                        pool_size=pool_size,
                        max_overflow=max_overflow,
                        pool_recycle=pool_recycle,
                        pool_pre_ping=pool_pre_ping,
                    )
                else:
                    database = Database(
                        database_url,
                        pool_size=pool_size,
                        max_overflow=max_overflow,
                        pool_recycle=pool_recycle,
                        pool_pre_ping=pool_pre_ping,
                    )
                should_manage_lifecycle = True

            # Always initialize database (safe to call multiple times)
            await database.init()

            set_database(database)
            app.state.database = database

            # Initialize scheduler if jobs are enabled
            if job_options is not None:
                from chapkit.core.scheduler import AIOJobScheduler

                scheduler = AIOJobScheduler(max_concurrency=job_options.max_concurrency)
                set_scheduler(scheduler)
                app.state.scheduler = scheduler

            # Log auth configuration after logging is configured
            if hasattr(app.state, "auth_source"):
                auth_source = app.state.auth_source
                key_count = app.state.auth_key_count

                if auth_source == "direct_keys":
                    logger.warning(
                        "auth.direct_keys",
                        message="Using direct API keys - not recommended for production",
                        count=key_count,
                    )
                elif auth_source.startswith("file:"):
                    file_path = auth_source.split(":", 1)[1]
                    logger.info("auth.loaded_from_file", file=file_path, count=key_count)
                elif auth_source.startswith("env:"):
                    parts = auth_source.split(":", 2)
                    env_var = parts[1]
                    if len(parts) > 2 and parts[2] == "empty":
                        logger.warning(
                            "auth.no_keys",
                            message=f"No API keys found in {env_var}. Service will reject all requests.",
                        )
                    else:
                        logger.info("auth.loaded_from_env", env_var=env_var, count=key_count)

            for hook in startup_hooks:
                await hook(app)
            try:
                yield
            finally:
                for hook in shutdown_hooks:
                    await hook(app)
                app.state.database = None

                # Dispose database only if we created it
                if should_manage_lifecycle:
                    await database.dispose()

        return lifespan

    @staticmethod
    def _create_database_health_check() -> HealthCheck:
        """Create database connectivity health check."""

        async def check_database() -> tuple[HealthState, str | None]:
            try:
                db = get_database()
                async with db.session() as session:
                    # Simple connectivity check - execute a trivial query
                    await session.execute(text("SELECT 1"))
                    return (HealthState.HEALTHY, None)
            except Exception as e:
                return (HealthState.UNHEALTHY, f"Database connection failed: {str(e)}")

        return check_database

    @staticmethod
    def _create_openapi_customizer(app: FastAPI) -> Callable[[], dict[str, Any]]:
        """Create OpenAPI schema customizer that cleans up generic type names."""

        def custom_openapi() -> dict[str, Any]:
            if app.openapi_schema:
                return app.openapi_schema

            from fastapi.openapi.utils import get_openapi

            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )

            # Clean up schema titles by removing generic type parameters
            if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
                schemas = openapi_schema["components"]["schemas"]
                cleaned_schemas: dict[str, Any] = {}

                for schema_name, schema_def in schemas.items():
                    # Remove generic type parameters from schema names
                    clean_name = re.sub(r"\[.*?\]", "", schema_name)
                    # If title exists in schema, clean it too
                    if isinstance(schema_def, dict) and "title" in schema_def:
                        schema_def["title"] = re.sub(r"\[.*?\]", "", schema_def["title"])
                    cleaned_schemas[clean_name] = schema_def

                openapi_schema["components"]["schemas"] = cleaned_schemas

                # Update all $ref pointers to use cleaned names
                def clean_refs(obj: Any) -> Any:
                    if isinstance(obj, dict):
                        if "$ref" in obj:
                            obj["$ref"] = re.sub(r"\[.*?\]", "", obj["$ref"])
                        for value in obj.values():
                            clean_refs(value)
                    elif isinstance(obj, list):
                        for item in obj:
                            clean_refs(item)

                clean_refs(openapi_schema)

            app.openapi_schema = openapi_schema
            return app.openapi_schema

        return custom_openapi

    @staticmethod
    def _install_info_endpoint(app: FastAPI, *, info: ServiceInfo) -> None:
        """Install service info endpoint."""
        info_type = type(info)

        @app.get("/api/v1/info", tags=["Service"], include_in_schema=True, response_model=info_type)
        async def get_info() -> ServiceInfo:
            return info

    # --------------------------------------------------------------------- Convenience

    @classmethod
    def create(cls, *, info: ServiceInfo, **kwargs: Any) -> FastAPI:
        """Create and build a FastAPI application in one call."""
        return cls(info=info, **kwargs).build()
