"""Example: API with API key authentication.

This example demonstrates how to add simple API key authentication to a chapkit service.

Run with environment variable:
    export CHAPKIT_API_KEYS="sk_dev_abc123,sk_dev_xyz789"
    fastapi dev examples/authenticated_api.py

Test:
    # Without API key (fails with 401)
    curl http://localhost:8000/api/v1/config

    # With valid API key (succeeds)
    curl -H "X-API-Key: sk_dev_abc123" http://localhost:8000/api/v1/config

    # Health check doesn't require auth
    curl http://localhost:8000/api/v1/health
"""

from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo


class AppConfig(BaseConfig):
    """Application configuration."""

    environment: str
    debug: bool = False


app = (
    ServiceBuilder(info=ServiceInfo(display_name="Authenticated API Example"))
    .with_logging()
    .with_health()
    .with_config(AppConfig)
    .with_auth(
        # For this example, using direct keys (NOT recommended for production!)
        # In production, use one of these instead:
        #   .with_auth()  # Reads from CHAPKIT_API_KEYS env var (recommended)
        #   .with_auth(api_key_file="/run/secrets/api_keys")  # Docker secrets
        api_keys=["sk_dev_abc123", "sk_dev_xyz789"],
    )
    .build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("authenticated_api:app")
