"""Monitoring example with OpenTelemetry and Prometheus metrics."""

from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo


class AppConfig(BaseConfig):
    """Example configuration schema."""

    api_key: str
    max_connections: int = 10


app = (
    ServiceBuilder(
        info=ServiceInfo(
            display_name="Monitoring Example Service",
            version="1.0.0",
            summary="Service with OpenTelemetry monitoring and Prometheus metrics",
            description="Demonstrates automatic instrumentation of FastAPI and SQLAlchemy "
            "with metrics exposed at /metrics endpoint. Includes health check and config endpoints.",
        )
    )
    .with_database()
    .with_health()
    .with_system()
    .with_config(AppConfig)
    .with_monitoring()  # Enables OpenTelemetry with Prometheus endpoint at /metrics
    .with_logging()
    .build()
)


if __name__ == "__main__":
    from chapkit.core.api.utilities import run_app

    run_app("monitoring_api:app")
