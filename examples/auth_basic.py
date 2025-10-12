"""Example API with API key authentication."""

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

    run_app("auth_basic:app")
