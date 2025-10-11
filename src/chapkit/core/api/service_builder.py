"""Base service builder for FastAPI applications without module dependencies."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncIterator, Awaitable, Callable, Dict, List, Self

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from chapkit.core import Database
from chapkit.core.logging import configure_logging

from .dependencies import get_database, get_scheduler, set_database, set_scheduler
from .middleware import add_error_handlers, add_logging_middleware
from .routers import HealthRouter, JobRouter, SystemRouter
from .routers.health import HealthCheck, HealthState


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
        self._database_url = database_url
        self._database_instance: Database | None = None
        self._title = self.info.display_name
        self._app_description = self.info.summary or self.info.description or ""
        self._version = self.info.version
        self._include_error_handlers = include_error_handlers
        self._include_logging = include_logging
        self._include_landing_page = False
        self._health_options: tuple[str, List[str], dict[str, HealthCheck]] | None = None
        self._system_options: tuple[str, List[str]] | None = None
        self._job_options: tuple[str, List[str], int | None] | None = None
        self._custom_routers: List[APIRouter] = []
        self._dependency_overrides: Dict[Callable[..., object], Callable[..., object]] = {}
        self._startup_hooks: List[Callable[[FastAPI], Awaitable[None]]] = []
        self._shutdown_hooks: List[Callable[[FastAPI], Awaitable[None]]] = []

    # --------------------------------------------------------------------- Fluent configuration

    def with_database(self, url: str) -> Self:
        """Configure database URL."""
        self._database_url = url
        return self

    def with_database_instance(self, database: Database) -> Self:
        """Inject a pre-configured database instance."""
        self._database_instance = database
        return self

    def with_landing_page(self) -> Self:
        """Enable landing page at root path."""
        self._include_landing_page = True
        return self

    def with_logging(self, enabled: bool = True) -> Self:
        """Enable structured logging with request tracing."""
        self._include_logging = enabled
        return self

    def with_health(
        self,
        *,
        prefix: str = "/api/v1/health",
        tags: List[str] | None = None,
        checks: dict[str, HealthCheck] | None = None,
        include_database_check: bool = True,
    ) -> Self:
        """Add health check endpoint with optional custom checks."""
        health_checks = checks or {}

        if include_database_check:
            health_checks["database"] = self._create_database_health_check()

        self._health_options = (prefix, list(tags) if tags is not None else ["health"], health_checks)
        return self

    def with_system(
        self,
        *,
        prefix: str = "/api/v1/system",
        tags: List[str] | None = None,
    ) -> Self:
        """Add system info endpoint."""
        self._system_options = (prefix, list(tags) if tags is not None else ["system"])
        return self

    def with_jobs(
        self,
        *,
        prefix: str = "/api/v1/jobs",
        tags: List[str] | None = None,
        max_concurrency: int | None = None,
    ) -> Self:
        """Add job scheduler endpoints."""
        self._job_options = (prefix, list(tags) if tags is not None else ["jobs"], max_concurrency)
        return self

    def include_router(self, router: APIRouter) -> Self:
        """Include a custom router."""
        self._custom_routers.append(router)
        return self

    def override_dependency(self, dependency: Callable[..., object], override: Callable[..., object]) -> Self:
        """Override a dependency for testing or customization."""
        self._dependency_overrides[dependency] = override
        return self

    def on_startup(self, hook: Callable[[FastAPI], Awaitable[None]]) -> Self:
        """Register a startup hook."""
        self._startup_hooks.append(hook)
        return self

    def on_shutdown(self, hook: Callable[[FastAPI], Awaitable[None]]) -> Self:
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

        if self._health_options:
            prefix, tags, checks = self._health_options
            health_router = HealthRouter.create(prefix=prefix, tags=tags, checks=checks)
            app.include_router(health_router)

        if self._system_options:
            prefix, tags = self._system_options
            system_router = SystemRouter.create(prefix=prefix, tags=tags)
            app.include_router(system_router)

        if self._job_options:
            prefix, tags, _ = self._job_options
            job_router = JobRouter.create(prefix=prefix, tags=tags, scheduler_factory=get_scheduler)
            app.include_router(job_router)

        # Extension point for module-specific routers
        self._register_module_routers(app)

        for router in self._custom_routers:
            app.include_router(router)

        for dependency, override in self._dependency_overrides.items():
            app.dependency_overrides[dependency] = override

        self._install_info_endpoint(app, info=self.info)

        if self._include_landing_page:
            self._install_landing_page(app, info=self.info)

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
            _, _, checks = self._health_options
            for name in checks.keys():
                if not name.replace("_", "").replace("-", "").isalnum():
                    raise ValueError(
                        f"Health check name '{name}' contains invalid characters. "
                        "Only alphanumeric characters, underscores, and hyphens are allowed."
                    )

    def _build_lifespan(self) -> Callable[[FastAPI], AsyncContextManager[None]]:
        """Build lifespan context manager for app startup/shutdown."""
        database_url = self._database_url
        database_instance = self._database_instance
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
                database = Database(database_url)
                should_manage_lifecycle = True

            # Always initialize database (safe to call multiple times)
            await database.init()

            set_database(database)
            app.state.database = database

            # Initialize scheduler if jobs are enabled
            if job_options is not None:
                from chapkit.core.scheduler import AIOJobScheduler

                _, _, max_concurrency = job_options
                scheduler = AIOJobScheduler(max_concurrency=max_concurrency)
                set_scheduler(scheduler)
                app.state.scheduler = scheduler

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

        @app.get("/api/v1/info", include_in_schema=False, response_model=info_type)
        async def get_info() -> ServiceInfo:
            return info

    @staticmethod
    def _install_landing_page(app: FastAPI, *, info: ServiceInfo) -> None:
        """Install landing page at root path."""
        from importlib.resources import files

        from fastapi.responses import HTMLResponse

        template_content = files("chapkit.core.api.templates").joinpath("landing_page.html").read_text()

        @app.get("/", include_in_schema=False, response_class=HTMLResponse)
        async def landing_page() -> str:
            return template_content

    # --------------------------------------------------------------------- Convenience

    @classmethod
    def create(cls, *, info: ServiceInfo, **kwargs: Any) -> FastAPI:
        """Create and build a FastAPI application in one call."""
        return cls(info=info, **kwargs).build()
