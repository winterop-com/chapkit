"""Class-based ML example with custom ModelRunner subclass.

This example demonstrates:
- Subclassing BaseModelRunner for OOP-style ML workflows
- Using lifecycle hooks (on_init, on_cleanup)
- Sharing state between train and predict (feature names, scaler)
- Feature preprocessing with StandardScaler
- Building a service with class-based runner

Run with: fastapi dev examples/ml_class.py
"""

from typing import Any

import pandas as pd
import structlog
from geojson_pydantic import FeatureCollection
from sklearn.linear_model import LinearRegression  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from chapkit import BaseConfig
from chapkit.api import AssessedStatus, MLServiceBuilder, MLServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy
from chapkit.modules.ml import BaseModelRunner

log = structlog.get_logger()


class WeatherConfig(BaseConfig):
    """Configuration for weather-based prediction model."""

    min_samples: int = 5
    normalize_features: bool = True


class WeatherModelRunner(BaseModelRunner):
    """Custom model runner with preprocessing and shared state."""

    def __init__(self) -> None:
        """Initialize runner with shared state."""
        self.feature_names: list[str] = ["rainfall", "mean_temperature", "humidity"]
        self.target_name: str = "disease_cases"
        self.scaler: StandardScaler | None = None  # type: ignore[no-any-unimported]
        self.initialized: bool = False

    async def on_init(self) -> None:
        """Initialize runner before training or prediction."""
        log.info("runner_initializing", features=self.feature_names)
        self.initialized = True

    async def on_cleanup(self) -> None:
        """Clean up resources after training or prediction."""
        log.info("runner_cleanup")
        self.initialized = False

    async def on_train(
        self,
        config: BaseConfig,
        data: pd.DataFrame,
        geo: FeatureCollection | None = None,
    ) -> Any:
        """Train a model with preprocessing and feature engineering.

        Args:
            config: Model configuration with training parameters
            data: Training data with features and target
            geo: Optional geospatial data

        Returns:
            Dict containing trained model and preprocessing artifacts
        """
        await self.on_init()

        try:
            # Cast config to expected type
            weather_config = WeatherConfig.model_validate(config.model_dump())
            log.info("training_started", config=weather_config.model_dump(), sample_count=len(data))

            # Validate minimum samples
            if len(data) < weather_config.min_samples:
                raise ValueError(f"Insufficient training data: {len(data)} < {weather_config.min_samples}")

            # Extract features and target
            X = data[self.feature_names].fillna(0)
            y = data[self.target_name].fillna(0)

            # Feature preprocessing
            if weather_config.normalize_features:
                self.scaler = StandardScaler()
                X_scaled = self.scaler.fit_transform(X)
                log.info(
                    "features_normalized",
                    mean=self.scaler.mean_.tolist(),  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
                    scale=self.scaler.scale_.tolist(),  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
                )
            else:
                X_scaled = X
                self.scaler = None

            # Train model
            model = LinearRegression()
            model.fit(X_scaled, y)

            log.info(
                "model_trained",
                features=self.feature_names,
                coefficients=model.coef_.tolist(),
                intercept=float(model.intercept_),
            )

            # Return model artifacts
            return {
                "model": model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                "config": weather_config.model_dump(),
            }

        finally:
            await self.on_cleanup()

    async def on_predict(
        self,
        config: BaseConfig,
        model: Any,
        historic: pd.DataFrame | None,
        future: pd.DataFrame,
        geo: FeatureCollection | None = None,
    ) -> pd.DataFrame:
        """Make predictions with preprocessing.

        Args:
            config: Model configuration
            model: Trained model artifacts (dict with model, scaler, etc.)
            historic: Optional historic data (not used in this example)
            future: Future data to make predictions on
            geo: Optional geospatial data

        Returns:
            DataFrame with predictions added as 'sample_0' column
        """
        await self.on_init()

        try:
            log.info("prediction_started", sample_count=len(future))

            # Extract model artifacts
            if isinstance(model, dict):
                trained_model = model["model"]
                scaler = model.get("scaler")
                feature_names = model["feature_names"]
            else:
                # Fallback for simple models
                trained_model = model
                scaler = None
                feature_names = self.feature_names

            # Extract features
            X = future[feature_names].fillna(0)

            # Apply same preprocessing as training
            if scaler is not None:
                X_scaled = scaler.transform(X)
            else:
                X_scaled = X

            # Make predictions
            y_pred = trained_model.predict(X_scaled)
            future["sample_0"] = y_pred

            log.info(
                "predictions_made",
                sample_count=len(y_pred),
                mean_prediction=float(y_pred.mean()),
                std_prediction=float(y_pred.std()),
            )

            return future

        finally:
            await self.on_cleanup()


# Create ML service info with metadata
info = MLServiceInfo(
    display_name="Weather-Based Prediction Service",
    version="1.0.0",
    summary="Class-based ML service with preprocessing",
    description="Train and predict disease cases using normalized weather features with StandardScaler",
    author="Data Science Team",
    author_note="Improved feature normalization for better prediction accuracy",
    author_assessed_status=AssessedStatus.green,
    contact_email="datascience@example.com",
)

# Create artifact hierarchy for ML artifacts
HIERARCHY = ArtifactHierarchy(
    name="weather_ml_pipeline",
    level_labels={0: "trained_model", 1: "predictions"},
)

# Create class-based model runner
runner = WeatherModelRunner()

# Build the FastAPI application
app = MLServiceBuilder(
    info=info,
    config_schema=WeatherConfig,
    hierarchy=HIERARCHY,
    runner=runner,
).build()


if __name__ == "__main__":
    from chapkit.api import run_app

    run_app("ml_class:app")
