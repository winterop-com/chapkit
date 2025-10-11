"""Tests for config_artifact_api example using TestClient.

This example demonstrates config-artifact linking and custom health checks.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from examples.config_artifact_api import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient for testing with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_landing_page(client: TestClient) -> None:
    """Test landing page returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_health_endpoint_with_custom_checks(client: TestClient) -> None:
    """Test health check includes custom flaky_service check."""
    response = client.get("/api/v1/health")
    # Can be healthy or unhealthy due to flaky check
    assert response.status_code in [200, 503]
    data = response.json()

    # Health endpoint returns HealthResponse which has status field
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

    assert "checks" in data
    assert "database" in data["checks"]
    assert "flaky_service" in data["checks"]

    # Flaky service check should have one of three states (using "state" key)
    flaky_check = data["checks"]["flaky_service"]
    assert flaky_check["state"] in ["healthy", "degraded", "unhealthy"]


def test_info_endpoint(client: TestClient) -> None:
    """Test service info endpoint returns service metadata."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Chapkit Config & Artifact Service"
    assert data["summary"] == "Linked config and artifact CRUD example"
    assert "hierarchy" in data
    assert data["hierarchy"]["name"] == "training_pipeline"
    assert "configs" in data
    assert len(data["configs"]) == 2


def test_list_configs(client: TestClient) -> None:
    """Test listing all seeded configs."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()

    # Should be a list of 2 seeded configs
    assert isinstance(data, list)
    assert len(data) == 2

    # Check config names
    names = {config["name"] for config in data}
    assert names == {"experiment_alpha", "experiment_beta"}


def test_list_artifacts(client: TestClient) -> None:
    """Test listing all seeded artifacts."""
    response = client.get("/api/v1/artifacts")
    assert response.status_code == 200
    data = response.json()

    # Should be a list of artifacts
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_artifact_tree(client: TestClient) -> None:
    """Test retrieving artifact tree structure."""
    # experiment_alpha root artifact
    root_id = "01K72PWT05GEXK1S24AVKAZ9VF"
    response = client.get(f"/api/v1/artifacts/{root_id}/$tree")
    assert response.status_code == 200
    tree = response.json()

    assert tree["id"] == root_id
    assert tree["data"]["stage"] == "train"
    assert "children" in tree
    assert len(tree["children"]) == 2  # Two predict runs


def test_get_linked_artifacts_for_config(client: TestClient) -> None:
    """Test retrieving artifacts linked to a config."""
    # Get experiment_alpha config
    configs_response = client.get("/api/v1/config")
    configs = configs_response.json()
    alpha_config = next((c for c in configs if c["name"] == "experiment_alpha"), None)
    assert alpha_config is not None

    config_id = alpha_config["id"]
    response = client.get(f"/api/v1/config/{config_id}/$artifacts")
    assert response.status_code == 200
    artifacts = response.json()

    # Should have linked artifacts
    assert isinstance(artifacts, list)
    assert len(artifacts) > 0

    # Verify it's the root artifact
    root_artifact = artifacts[0]
    assert root_artifact["id"] == "01K72PWT05GEXK1S24AVKAZ9VF"


def test_get_config_for_artifact(client: TestClient) -> None:
    """Test retrieving config linked to an artifact."""
    # experiment_alpha root artifact
    artifact_id = "01K72PWT05GEXK1S24AVKAZ9VF"
    response = client.get(f"/api/v1/artifacts/{artifact_id}/$config")
    assert response.status_code == 200
    config = response.json()

    # Should return the experiment_alpha config
    assert config["name"] == "experiment_alpha"
    assert "data" in config
    assert config["data"]["model"] == "xgboost"
    assert config["data"]["learning_rate"] == 0.05


def test_link_artifact_to_config(client: TestClient) -> None:
    """Test linking an artifact to a config."""
    # Create a new config
    new_config = {
        "name": "test-experiment",
        "data": {"model": "random_forest", "learning_rate": 0.01, "epochs": 100, "batch_size": 128},
    }
    create_response = client.post("/api/v1/config", json=new_config)
    assert create_response.status_code == 201
    config = create_response.json()
    config_id = config["id"]

    # Create a root artifact
    new_artifact = {"data": {"stage": "train", "dataset": "test_data.parquet"}}
    artifact_response = client.post("/api/v1/artifacts", json=new_artifact)
    assert artifact_response.status_code == 201
    artifact = artifact_response.json()
    artifact_id = artifact["id"]

    # Link the artifact to the config
    link_response = client.post(f"/api/v1/config/{config_id}/$link-artifact", json={"artifact_id": artifact_id})
    assert link_response.status_code == 204

    # Verify the link
    artifacts_response = client.get(f"/api/v1/config/{config_id}/$artifacts")
    assert artifacts_response.status_code == 200
    linked_artifacts = artifacts_response.json()
    assert len(linked_artifacts) == 1
    assert linked_artifacts[0]["id"] == artifact_id


def test_link_non_root_artifact_fails(client: TestClient) -> None:
    """Test that linking a non-root artifact to config fails."""
    # Get experiment_alpha config
    configs_response = client.get("/api/v1/config")
    configs = configs_response.json()
    alpha_config = next((c for c in configs if c["name"] == "experiment_alpha"), None)
    assert alpha_config is not None
    config_id = alpha_config["id"]

    # Try to link a non-root artifact (level > 0)
    # This is a child artifact from experiment_alpha
    non_root_artifact_id = "01K72PWT05GEXK1S24AVKAZ9VG"

    link_response = client.post(
        f"/api/v1/config/{config_id}/$link-artifact", json={"artifact_id": non_root_artifact_id}
    )
    # Should fail because non-root artifacts can't be linked
    assert link_response.status_code == 400
    data = link_response.json()
    assert "root" in data["detail"].lower() or "level 0" in data["detail"].lower()


def test_unlink_artifact_from_config(client: TestClient) -> None:
    """Test unlinking an artifact from a config."""
    # Create config and artifact
    new_config = {
        "name": "unlink-test",
        "data": {"model": "mlp", "learning_rate": 0.001, "epochs": 50, "batch_size": 64},
    }
    config_response = client.post("/api/v1/config", json=new_config)
    config = config_response.json()
    config_id = config["id"]

    new_artifact = {"data": {"stage": "train", "dataset": "unlink_test.parquet"}}
    artifact_response = client.post("/api/v1/artifacts", json=new_artifact)
    artifact = artifact_response.json()
    artifact_id = artifact["id"]

    # Link them
    client.post(f"/api/v1/config/{config_id}/$link-artifact", json={"artifact_id": artifact_id})

    # Unlink
    unlink_response = client.post(f"/api/v1/config/{config_id}/$unlink-artifact", json={"artifact_id": artifact_id})
    assert unlink_response.status_code == 204

    # Verify unlinked
    artifacts_response = client.get(f"/api/v1/config/{config_id}/$artifacts")
    linked_artifacts = artifacts_response.json()
    assert len(linked_artifacts) == 0


def test_create_config_with_experiment_schema(client: TestClient) -> None:
    """Test creating a config with ExperimentConfig schema."""
    new_config = {
        "name": "test-ml-config",
        "data": {"model": "svm", "learning_rate": 0.1, "epochs": 30, "batch_size": 512},
    }

    response = client.post("/api/v1/config", json=new_config)
    assert response.status_code == 201
    data = response.json()

    assert data["name"] == "test-ml-config"
    assert data["data"]["model"] == "svm"
    assert data["data"]["epochs"] == 30


def test_create_artifact_in_hierarchy(client: TestClient) -> None:
    """Test creating artifacts following the training_pipeline hierarchy."""
    # Create root (train level)
    train_artifact = {"data": {"stage": "train", "dataset": "new_train.parquet"}}
    train_response = client.post("/api/v1/artifacts", json=train_artifact)
    assert train_response.status_code == 201
    train = train_response.json()
    train_id = train["id"]
    assert train["level"] == 0

    # Create child (predict level)
    predict_artifact = {
        "parent_id": train_id,
        "data": {"stage": "predict", "run": "2024-03-01", "path": "predictions.parquet"},
    }
    predict_response = client.post("/api/v1/artifacts", json=predict_artifact)
    assert predict_response.status_code == 201
    predict = predict_response.json()
    predict_id = predict["id"]
    assert predict["level"] == 1
    assert predict["parent_id"] == train_id

    # Create grandchild (result level)
    result_artifact = {"parent_id": predict_id, "data": {"stage": "result", "metrics": {"accuracy": 0.95}}}
    result_response = client.post("/api/v1/artifacts", json=result_artifact)
    assert result_response.status_code == 201
    result = result_response.json()
    assert result["level"] == 2
    assert result["parent_id"] == predict_id

    # Verify tree structure
    tree_response = client.get(f"/api/v1/artifacts/{train_id}/$tree")
    tree = tree_response.json()
    assert len(tree["children"]) == 1
    assert tree["children"][0]["id"] == predict_id
    assert len(tree["children"][0]["children"]) == 1
