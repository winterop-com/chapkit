"""Example authenticated ML service for disease prediction with API key security."""

from typing import Any

import pandas as pd
from geojson_pydantic import FeatureCollection
from sklearn.linear_model import LinearRegression  # type: ignore[import-untyped]

from chapkit import BaseConfig
from chapkit.api import MLServiceBuilder, ServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy
from chapkit.modules.ml import FunctionalModelRunner


class SecureMLConfig(BaseConfig):
    """Configuration for secure ML service."""

    pass  # Minimal config for this example


async def on_train(
    config: SecureMLConfig,
    data: pd.DataFrame,
    geo: FeatureCollection | None = None,
) -> Any:
    """Train a linear regression model for disease prediction."""
    features = ["rainfall", "mean_temperature"]
    X = data[features]
    Y = data["disease_cases"].fillna(0)

    model = LinearRegression()
    model.fit(X, Y)
    return model


async def on_predict(
    config: SecureMLConfig,
    model: Any,
    historic: pd.DataFrame | None,
    future: pd.DataFrame,
    geo: FeatureCollection | None = None,
) -> pd.DataFrame:
    """Make predictions using trained model."""
    X = future[["rainfall", "mean_temperature"]]
    future["sample_0"] = model.predict(X)
    return future


runner = FunctionalModelRunner(on_train=on_train, on_predict=on_predict)

HIERARCHY = ArtifactHierarchy(
    name="secure_ml_pipeline",
    level_labels={0: "trained_model", 1: "predictions"},
)

# Build ML service with authentication using MLServiceBuilder
app = (
    MLServiceBuilder(
        info=ServiceInfo(
            display_name="Authenticated Disease Prediction ML Service",
            version="1.0.0",
            summary="Secure ML service with API key authentication",
            description=(
                "Disease prediction ML service with API key authentication. "
                "All ML endpoints (train, predict, config, artifacts) require valid API key. "
                "Health checks and documentation remain publicly accessible."
            ),
            contact={"email": "ml-ops@example.com"},
            license_info={"name": "MIT"},
        ),
        database_url="sqlite+aiosqlite:///./secure_ml.db",
        config_schema=SecureMLConfig,
        hierarchy=HIERARCHY,
        runner=runner,
    )
    .with_auth()  # Enable authentication - reads from CHAPKIT_API_KEYS
    .build()
)


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("auth_ml_service:app")
