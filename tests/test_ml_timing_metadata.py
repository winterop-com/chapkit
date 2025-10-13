"""Tests for ML timing metadata capture."""

import asyncio
import datetime

import pandas as pd
import pytest
from geojson_pydantic import FeatureCollection
from ulid import ULID

from chapkit.core import SqliteDatabaseBuilder
from chapkit.core.scheduler import AIOJobScheduler
from chapkit.modules.artifact import ArtifactManager, ArtifactRepository
from chapkit.modules.artifact.schemas import PandasDataFrame
from chapkit.modules.config import BaseConfig, ConfigIn, ConfigManager, ConfigRepository
from chapkit.modules.ml import FunctionalModelRunner, MLManager, PredictRequest, TrainRequest


class SimpleConfig(BaseConfig):
    """Simple test config."""

    value: int = 42


async def simple_train(
    config: BaseConfig,
    data: pd.DataFrame,
    geo: FeatureCollection | None = None,
) -> dict[str, int]:
    """Simple training function that takes measurable time."""
    await asyncio.sleep(0.1)  # Simulate training time
    return {"trained": True, "samples": len(data)}


async def simple_predict(
    config: BaseConfig,
    model: dict[str, int],
    historic: pd.DataFrame | None,
    future: pd.DataFrame,
    geo: FeatureCollection | None = None,
) -> pd.DataFrame:
    """Simple prediction function that takes measurable time."""
    await asyncio.sleep(0.05)  # Simulate prediction time
    future["sample_0"] = 1.0
    return future


@pytest.fixture
async def ml_manager():
    """Create ML manager for testing."""
    database = SqliteDatabaseBuilder().in_memory().build()
    await database.init()

    scheduler = AIOJobScheduler()

    runner = FunctionalModelRunner(on_train=simple_train, on_predict=simple_predict)

    manager = MLManager(runner, scheduler, database, SimpleConfig)
    yield manager


@pytest.fixture
async def setup_data(ml_manager: MLManager):
    """Set up test data for ML operations."""
    # Create config
    async with ml_manager.database.session() as session:
        config_repo = ConfigRepository(session)
        config_manager = ConfigManager[SimpleConfig](config_repo, SimpleConfig)
        config = await config_manager.save(ConfigIn(name="test", data=SimpleConfig(value=42)))
        await config_repo.commit()

    # Create training data
    train_df = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6], "target": [7, 8, 9]})

    # Create prediction data
    predict_df = pd.DataFrame({"feature1": [10, 11], "feature2": [12, 13]})

    return config.id, train_df, predict_df


async def test_training_timing_metadata_captured(
    ml_manager: MLManager, setup_data: tuple[ULID, pd.DataFrame, pd.DataFrame]
):
    """Test that training timing metadata is captured correctly."""
    config_id, train_df, _ = setup_data

    # Submit training job
    train_request = TrainRequest(
        config_id=config_id,
        data=PandasDataFrame.from_dataframe(train_df),
    )

    response = await ml_manager.execute_train(train_request)

    # Wait for job to complete
    await asyncio.sleep(0.5)

    # Retrieve trained model artifact
    async with ml_manager.database.session() as session:
        artifact_repo = ArtifactRepository(session)
        artifact_manager = ArtifactManager(artifact_repo)
        artifact = await artifact_manager.find_by_id(ULID.from_str(response.model_artifact_id))

    assert artifact is not None
    assert artifact.data["ml_type"] == "trained_model"

    # Verify timing metadata exists
    assert "training_started_at" in artifact.data
    assert "training_completed_at" in artifact.data
    assert "training_duration_seconds" in artifact.data

    # Verify timing values are reasonable
    started_at = datetime.datetime.fromisoformat(artifact.data["training_started_at"])
    completed_at = datetime.datetime.fromisoformat(artifact.data["training_completed_at"])
    duration = artifact.data["training_duration_seconds"]

    assert isinstance(started_at, datetime.datetime)
    assert isinstance(completed_at, datetime.datetime)
    assert isinstance(duration, (int, float))

    # Verify timing makes sense (completed after started)
    assert completed_at > started_at

    # Verify duration roughly matches sleep time (0.1s + overhead)
    assert 0.05 < duration < 1.0

    # Verify duration matches calculated difference
    calculated_duration = (completed_at - started_at).total_seconds()
    assert abs(duration - calculated_duration) < 0.01


async def test_prediction_timing_metadata_captured(
    ml_manager: MLManager, setup_data: tuple[ULID, pd.DataFrame, pd.DataFrame]
):
    """Test that prediction timing metadata is captured correctly."""
    config_id, train_df, predict_df = setup_data

    # Train model first
    train_request = TrainRequest(
        config_id=config_id,
        data=PandasDataFrame.from_dataframe(train_df),
    )
    train_response = await ml_manager.execute_train(train_request)

    # Wait for training to complete
    await asyncio.sleep(0.5)

    # Submit prediction job
    predict_request = PredictRequest(
        model_artifact_id=ULID.from_str(train_response.model_artifact_id),
        future=PandasDataFrame.from_dataframe(predict_df),
    )
    predict_response = await ml_manager.execute_predict(predict_request)

    # Wait for prediction to complete
    await asyncio.sleep(0.5)

    # Retrieve prediction artifact
    async with ml_manager.database.session() as session:
        artifact_repo = ArtifactRepository(session)
        artifact_manager = ArtifactManager(artifact_repo)
        artifact = await artifact_manager.find_by_id(ULID.from_str(predict_response.prediction_artifact_id))

    assert artifact is not None
    assert artifact.data["ml_type"] == "prediction"

    # Verify timing metadata exists
    assert "prediction_started_at" in artifact.data
    assert "prediction_completed_at" in artifact.data
    assert "prediction_duration_seconds" in artifact.data

    # Verify timing values are reasonable
    started_at = datetime.datetime.fromisoformat(artifact.data["prediction_started_at"])
    completed_at = datetime.datetime.fromisoformat(artifact.data["prediction_completed_at"])
    duration = artifact.data["prediction_duration_seconds"]

    assert isinstance(started_at, datetime.datetime)
    assert isinstance(completed_at, datetime.datetime)
    assert isinstance(duration, (int, float))

    # Verify timing makes sense
    assert completed_at > started_at

    # Verify duration roughly matches sleep time (0.05s + overhead)
    assert 0.01 < duration < 1.0

    # Verify duration matches calculated difference
    calculated_duration = (completed_at - started_at).total_seconds()
    assert abs(duration - calculated_duration) < 0.01


async def test_timing_metadata_iso_format(ml_manager: MLManager, setup_data: tuple[ULID, pd.DataFrame, pd.DataFrame]):
    """Test that timestamps are in ISO format."""
    config_id, train_df, _ = setup_data

    train_request = TrainRequest(
        config_id=config_id,
        data=PandasDataFrame.from_dataframe(train_df),
    )
    response = await ml_manager.execute_train(train_request)
    await asyncio.sleep(0.5)

    async with ml_manager.database.session() as session:
        artifact_repo = ArtifactRepository(session)
        artifact_manager = ArtifactManager(artifact_repo)
        artifact = await artifact_manager.find_by_id(ULID.from_str(response.model_artifact_id))

    assert artifact is not None
    # Verify ISO format can be parsed
    started_str = artifact.data["training_started_at"]
    completed_str = artifact.data["training_completed_at"]

    # These should not raise exceptions
    started = datetime.datetime.fromisoformat(started_str)
    completed = datetime.datetime.fromisoformat(completed_str)

    # Verify timezone info exists (UTC)
    assert started.tzinfo is not None
    assert completed.tzinfo is not None


async def test_timing_duration_rounded_to_two_decimals(
    ml_manager: MLManager, setup_data: tuple[ULID, pd.DataFrame, pd.DataFrame]
):
    """Test that duration is rounded to 2 decimal places."""
    config_id, train_df, _ = setup_data

    train_request = TrainRequest(
        config_id=config_id,
        data=PandasDataFrame.from_dataframe(train_df),
    )
    response = await ml_manager.execute_train(train_request)
    await asyncio.sleep(0.5)

    async with ml_manager.database.session() as session:
        artifact_repo = ArtifactRepository(session)
        artifact_manager = ArtifactManager(artifact_repo)
        artifact = await artifact_manager.find_by_id(ULID.from_str(response.model_artifact_id))

    assert artifact is not None
    duration = artifact.data["training_duration_seconds"]

    # Verify precision (should have at most 2 decimal places)
    duration_str = str(duration)
    if "." in duration_str:
        decimal_places = len(duration_str.split(".")[1])
        assert decimal_places <= 2


async def test_original_metadata_preserved(ml_manager: MLManager, setup_data: tuple[ULID, pd.DataFrame, pd.DataFrame]):
    """Test that original metadata fields are still present."""
    config_id, train_df, predict_df = setup_data

    # Train model
    train_request = TrainRequest(
        config_id=config_id,
        data=PandasDataFrame.from_dataframe(train_df),
    )
    train_response = await ml_manager.execute_train(train_request)
    await asyncio.sleep(0.5)

    # Check training artifact
    async with ml_manager.database.session() as session:
        artifact_repo = ArtifactRepository(session)
        artifact_manager = ArtifactManager(artifact_repo)
        train_artifact = await artifact_manager.find_by_id(ULID.from_str(train_response.model_artifact_id))

    # Original fields should still exist
    assert train_artifact is not None
    assert train_artifact.data["ml_type"] == "trained_model"
    assert train_artifact.data["config_id"] == str(config_id)
    assert "model" in train_artifact.data

    # Predict
    predict_request = PredictRequest(
        model_artifact_id=ULID.from_str(train_response.model_artifact_id),
        future=PandasDataFrame.from_dataframe(predict_df),
    )
    predict_response = await ml_manager.execute_predict(predict_request)
    await asyncio.sleep(0.5)

    # Check prediction artifact
    async with ml_manager.database.session() as session:
        artifact_repo = ArtifactRepository(session)
        artifact_manager = ArtifactManager(artifact_repo)
        predict_artifact = await artifact_manager.find_by_id(ULID.from_str(predict_response.prediction_artifact_id))

    # Original fields should still exist
    assert predict_artifact is not None
    assert predict_artifact.data["ml_type"] == "prediction"
    assert predict_artifact.data["model_artifact_id"] == str(train_response.model_artifact_id)
    assert predict_artifact.data["config_id"] == str(config_id)
    assert "predictions" in predict_artifact.data
