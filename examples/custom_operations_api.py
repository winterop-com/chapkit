"""FastAPI service demonstrating custom operations with various HTTP methods."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from ulid import ULID

from chapkit import BaseConfig, ConfigIn, ConfigManager, ConfigOut
from chapkit.api import ServiceBuilder, ServiceInfo
from chapkit.api.dependencies import get_config_manager
from chapkit.core.api import CrudRouter
from chapkit.core.exceptions import ConflictError, NotFoundError


class FeatureConfig(BaseConfig):
    """Configuration with feature flag support."""

    name: str
    enabled: bool = True
    max_requests: int = 1000
    timeout_seconds: float = 30.0
    tags: list[str] = []


class ValidationResult(BaseModel):
    """Result of configuration validation."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class BulkToggleRequest(BaseModel):
    """Request to toggle multiple configs."""

    enabled: bool
    tag_filter: str | None = None


class StatsResponse(BaseModel):
    """Configuration statistics."""

    total: int
    enabled: int
    disabled: int
    avg_max_requests: float
    tags: dict[str, int]


class BulkToggleResponse(BaseModel):
    """Result of bulk toggle operation."""

    updated: int


class ResetResponse(BaseModel):
    """Result of reset operation."""

    reset: int


# Custom router with operations
def create_feature_router() -> APIRouter:
    """Create config router with custom operations."""
    router = CrudRouter[ConfigIn[FeatureConfig], ConfigOut[FeatureConfig]](
        prefix="/api/v1/configs",
        tags=["Config"],
        entity_in_type=ConfigIn[FeatureConfig],
        entity_out_type=ConfigOut[FeatureConfig],
        manager_factory=get_config_manager,  # type: ignore[arg-type]
    )

    # PATCH operation: Toggle enabled flag
    async def toggle_enabled(
        entity_id: str,
        enabled: bool,
        manager: Annotated[ConfigManager[FeatureConfig], Depends(get_config_manager)],
    ) -> ConfigOut[FeatureConfig]:
        """Enable or disable a feature configuration."""
        config_id = ULID.from_str(entity_id)
        config = await manager.find_by_id(config_id)

        if config is None:
            raise NotFoundError(f"Config {entity_id} not found", instance=f"/api/v1/configs/{entity_id}")

        # Create updated config with modified enabled flag
        updated_data = FeatureConfig(
            **config.data.model_dump(exclude={"enabled"}),
            enabled=enabled,
        )
        updated_config = ConfigIn[FeatureConfig](
            **config.model_dump(exclude={"created_at", "updated_at", "data"}),
            data=updated_data,
        )

        return await manager.save(updated_config)

    router.register_entity_operation(
        "enable",
        toggle_enabled,
        http_method="PATCH",
        response_model=ConfigOut[FeatureConfig],
        summary="Enable or disable config",
        description="Partial update to toggle the enabled flag",
    )

    # GET operation: Validate configuration
    async def validate_config(
        entity_id: str,
        manager: Annotated[ConfigManager[FeatureConfig], Depends(get_config_manager)],
    ) -> ValidationResult:
        """Validate a configuration against business rules."""
        config_id = ULID.from_str(entity_id)
        config = await manager.find_by_id(config_id)

        if config is None:
            raise NotFoundError(f"Config {entity_id} not found", instance=f"/api/v1/configs/{entity_id}")

        errors: list[str] = []
        warnings: list[str] = []

        # Validation rules
        if config.data.max_requests < 100:
            warnings.append("max_requests is very low (<100)")
        if config.data.max_requests > 10000:
            errors.append("max_requests exceeds maximum allowed (10000)")

        if config.data.timeout_seconds < 1:
            errors.append("timeout_seconds must be at least 1")
        if config.data.timeout_seconds > 300:
            warnings.append("timeout_seconds is very high (>5 minutes)")

        if not config.data.enabled:
            warnings.append("Configuration is currently disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    router.register_entity_operation(
        "validate",
        validate_config,
        http_method="GET",
        response_model=ValidationResult,
        summary="Validate configuration",
        description="Check configuration against business rules",
    )

    # POST operation: Duplicate configuration
    async def duplicate_config(
        entity_id: str,
        new_name: str,
        manager: Annotated[ConfigManager[FeatureConfig], Depends(get_config_manager)],
    ) -> ConfigOut[FeatureConfig]:
        """Create a duplicate of an existing configuration."""
        config_id = ULID.from_str(entity_id)
        config = await manager.find_by_id(config_id)

        if config is None:
            raise NotFoundError(f"Config {entity_id} not found", instance=f"/api/v1/configs/{entity_id}")

        # Check if name already exists
        if await manager.find_by_name(new_name):
            raise ConflictError(f"Config with name '{new_name}' already exists", instance="/api/v1/configs")

        # Create duplicate with new name
        duplicate = ConfigIn[FeatureConfig](
            name=new_name,
            data=FeatureConfig(**config.data.model_dump()),
        )

        return await manager.save(duplicate)

    router.register_entity_operation(
        "duplicate",
        duplicate_config,
        http_method="POST",
        response_model=ConfigOut[FeatureConfig],
        status_code=status.HTTP_201_CREATED,
        summary="Duplicate configuration",
        description="Create a copy of an existing config with a new name",
    )

    # PATCH collection operation: Bulk toggle
    async def bulk_toggle(
        request: BulkToggleRequest,
        manager: Annotated[ConfigManager[FeatureConfig], Depends(get_config_manager)],
    ) -> BulkToggleResponse:
        """Bulk enable or disable configurations."""
        all_configs = await manager.find_all()
        updated_count = 0

        for config in all_configs:
            # Apply tag filter if specified
            if request.tag_filter and request.tag_filter not in config.data.tags:
                continue

            # Update enabled flag
            updated_data = FeatureConfig(
                **config.data.model_dump(exclude={"enabled"}),
                enabled=request.enabled,
            )
            updated_config = ConfigIn[FeatureConfig](
                **config.model_dump(exclude={"created_at", "updated_at", "data"}),
                data=updated_data,
            )
            await manager.save(updated_config)
            updated_count += 1

        return BulkToggleResponse(updated=updated_count)

    router.register_collection_operation(
        "bulk-toggle",
        bulk_toggle,
        http_method="PATCH",
        response_model=BulkToggleResponse,
        summary="Bulk enable/disable configs",
        description="Enable or disable multiple configs, optionally filtered by tag",
    )

    # GET collection operation: Statistics
    async def get_stats(
        manager: Annotated[ConfigManager[FeatureConfig], Depends(get_config_manager)],
    ) -> StatsResponse:
        """Get statistics about all configurations."""
        all_configs = await manager.find_all()

        if not all_configs:
            return StatsResponse(
                total=0,
                enabled=0,
                disabled=0,
                avg_max_requests=0.0,
                tags={},
            )

        enabled_count = sum(1 for c in all_configs if c.data.enabled)
        total_requests = sum(c.data.max_requests for c in all_configs)
        avg_requests = total_requests / len(all_configs)

        # Count tag occurrences
        tag_counts: dict[str, int] = {}
        for config in all_configs:
            for tag in config.data.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return StatsResponse(
            total=len(all_configs),
            enabled=enabled_count,
            disabled=len(all_configs) - enabled_count,
            avg_max_requests=round(avg_requests, 2),
            tags=tag_counts,
        )

    router.register_collection_operation(
        "stats",
        get_stats,
        http_method="GET",
        response_model=StatsResponse,
        summary="Get configuration statistics",
        description="Retrieve aggregate statistics about all configs",
    )

    # POST collection operation: Reset all
    async def reset_all(
        manager: Annotated[ConfigManager[FeatureConfig], Depends(get_config_manager)],
    ) -> ResetResponse:
        """Reset all configurations to default values."""
        all_configs = await manager.find_all()
        reset_count = 0

        default_config = FeatureConfig(
            name="default",
            enabled=True,
            max_requests=1000,
            timeout_seconds=30.0,
            tags=[],
        )

        for config in all_configs:
            reset_data = FeatureConfig(
                **default_config.model_dump(exclude={"name"}),
                name=config.data.name,
            )
            updated_config = ConfigIn[FeatureConfig](
                **config.model_dump(exclude={"created_at", "updated_at", "data"}),
                data=reset_data,
            )
            await manager.save(updated_config)
            reset_count += 1

        return ResetResponse(reset=reset_count)

    router.register_collection_operation(
        "reset",
        reset_all,
        http_method="POST",
        response_model=ResetResponse,
        summary="Reset all configurations",
        description="Reset all configs to default values (destructive operation)",
    )

    return router.router


# Seed some example configurations
async def seed_features(app: FastAPI) -> None:
    """Seed example feature configurations."""
    from chapkit.core.api.dependencies import get_database

    database = get_database()

    async with database.session() as session:
        from chapkit import ConfigRepository

        repo = ConfigRepository(session)
        manager = ConfigManager[FeatureConfig](repo, FeatureConfig)

        await manager.delete_all()
        await manager.save_all(
            [
                ConfigIn[FeatureConfig](
                    id=ULID.from_str("01K72Q5N5KCRM6MD3BRE4P07NB"),
                    name="api_rate_limiting",
                    data=FeatureConfig(
                        name="API Rate Limiting",
                        enabled=True,
                        max_requests=5000,
                        timeout_seconds=60.0,
                        tags=["api", "security"],
                    ),
                ),
                ConfigIn[FeatureConfig](
                    id=ULID.from_str("01K72Q5N5KCRM6MD3BRE4P07NC"),
                    name="cache_optimization",
                    data=FeatureConfig(
                        name="Cache Optimization",
                        enabled=True,
                        max_requests=10000,
                        timeout_seconds=15.0,
                        tags=["performance", "cache"],
                    ),
                ),
                ConfigIn[FeatureConfig](
                    id=ULID.from_str("01K72Q5N5KCRM6MD3BRE4P07ND"),
                    name="experimental_features",
                    data=FeatureConfig(
                        name="Experimental Features",
                        enabled=False,
                        max_requests=100,
                        timeout_seconds=120.0,
                        tags=["experimental", "beta"],
                    ),
                ),
            ]
        )


# Build the application
info = ServiceInfo(
    display_name="Feature Configuration Service",
    summary="Config management with custom operations (PATCH, GET, POST, DELETE)",
    version="1.0.0",
)

app: FastAPI = (
    ServiceBuilder(info=info).with_health().include_router(create_feature_router()).on_startup(seed_features).build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("custom_operations_api:app")
