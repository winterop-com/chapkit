"""Example API with environment variable authentication for production deployments."""

from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo


class ProductionConfig(BaseConfig):
    """Production configuration with validation."""

    environment: str
    region: str = "us-east-1"
    enable_analytics: bool = True
    max_requests_per_minute: int = 1000


app = (
    ServiceBuilder(
        info=ServiceInfo(
            display_name="Production API with Environment Variable Auth",
            version="2.0.0",
            summary="Production-ready API using environment variables for authentication",
            description=(
                "Demonstrates the recommended approach for production deployments: "
                "reading API keys from CHAPKIT_API_KEYS environment variable. "
                "Supports multiple keys for zero-downtime rotation."
            ),
            contact={"email": "ops@example.com"},
            license_info={"name": "MIT"},
        ),
    )
    .with_logging()
    .with_health()
    .with_config(ProductionConfig)
    .with_auth()  # Reads from CHAPKIT_API_KEYS environment variable (recommended!)
    .build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("auth_envvar:app")
