"""Tests for ServiceBuilder validation."""

import pytest
from pydantic import Field

from chapkit import BaseConfig
from chapkit.api import ServiceBuilder
from chapkit.core.api.service_builder import ServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy
from chapkit.modules.ml import ModelRunnerProtocol


class DummyConfig(BaseConfig):
    """Dummy config for testing."""

    test_value: str = Field(default="test")


class DummyRunner(ModelRunnerProtocol):
    """Dummy ML runner for testing."""

    def train(self, data: dict, params: dict) -> dict:
        """Train a model."""
        return {"status": "trained"}

    def predict(self, model: dict, input_data: dict) -> dict:
        """Make predictions."""
        return {"predictions": []}


def test_tasks_without_artifacts_raises_error() -> None:
    """Test that tasks without artifacts raises ValueError."""
    builder = ServiceBuilder(info=ServiceInfo(display_name="Test"))

    with pytest.raises(ValueError, match="Task execution requires artifacts"):
        builder.with_tasks().build()


def test_ml_without_config_raises_error() -> None:
    """Test that ML without config raises ValueError."""
    builder = ServiceBuilder(info=ServiceInfo(display_name="Test"))
    hierarchy = ArtifactHierarchy(name="test")
    runner = DummyRunner()

    with pytest.raises(ValueError, match="ML operations require config"):
        builder.with_artifacts(hierarchy=hierarchy).with_ml(runner=runner).build()


def test_ml_without_artifacts_raises_error() -> None:
    """Test that ML without artifacts raises ValueError."""
    builder = ServiceBuilder(info=ServiceInfo(display_name="Test"))
    runner = DummyRunner()

    with pytest.raises(ValueError, match="ML operations require artifacts"):
        builder.with_config(DummyConfig).with_ml(runner=runner).build()


def test_ml_without_jobs_raises_error() -> None:
    """Test that ML without job scheduler raises ValueError."""
    builder = ServiceBuilder(info=ServiceInfo(display_name="Test"))
    hierarchy = ArtifactHierarchy(name="test")
    runner = DummyRunner()

    with pytest.raises(ValueError, match="ML operations require job scheduler"):
        builder.with_config(DummyConfig).with_artifacts(hierarchy=hierarchy).with_ml(runner=runner).build()


def test_artifacts_config_linking_without_config_raises_error() -> None:
    """Test that artifact config-linking without config raises ValueError."""
    builder = ServiceBuilder(info=ServiceInfo(display_name="Test"))
    hierarchy = ArtifactHierarchy(name="test")

    with pytest.raises(ValueError, match="Artifact config-linking requires a config schema"):
        builder.with_artifacts(hierarchy=hierarchy, enable_config_linking=True).build()


def test_valid_ml_service_builds_successfully() -> None:
    """Test that a properly configured ML service builds without errors."""
    builder = ServiceBuilder(info=ServiceInfo(display_name="Test"))
    hierarchy = ArtifactHierarchy(name="test")
    runner = DummyRunner()

    # This should build successfully with all dependencies
    app = (
        builder.with_config(DummyConfig)
        .with_artifacts(hierarchy=hierarchy)
        .with_jobs()
        .with_ml(runner=runner)
        .build()
    )

    assert app is not None
