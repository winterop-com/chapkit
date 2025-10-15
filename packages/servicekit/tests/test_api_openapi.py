"""Smoke test for OpenAPI schema generation with chapkit routers."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from servicekit import ArtifactIn, ArtifactOut, BaseConfig, ConfigIn, ConfigOut
from servicekit.api import ArtifactRouter, ConfigRouter

from tests._stubs import ArtifactManagerStub, ConfigManagerStub, singleton_factory


def test_openapi_schema_with_config_and_artifact_routers() -> None:
    app = FastAPI()

    config_router = ConfigRouter.create(
        prefix="/config",
        tags=["Config"],
        manager_factory=singleton_factory(ConfigManagerStub()),
        entity_in_type=ConfigIn[BaseConfig],
        entity_out_type=ConfigOut[BaseConfig],
    )

    artifact_router = ArtifactRouter.create(
        prefix="/artifacts",
        tags=["Artifacts"],
        manager_factory=singleton_factory(ArtifactManagerStub()),
        entity_in_type=ArtifactIn,
        entity_out_type=ArtifactOut,
    )

    app.include_router(config_router)
    app.include_router(artifact_router)

    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/config" in schema["paths"]
    assert "/artifacts" in schema["paths"]
    assert "/artifacts/{entity_id}/$tree" in schema["paths"]
