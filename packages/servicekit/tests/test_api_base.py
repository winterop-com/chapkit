"""Tests for the base API router abstraction."""

from typing import ClassVar, Sequence

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from servicekit.core.api.router import Router


class TrackingRouter(Router):
    """Test router that counts how many times routes are registered."""

    register_calls: ClassVar[int] = 0

    def _register_routes(self) -> None:
        type(self).register_calls += 1

        @self.router.get("/")
        async def read_root() -> dict[str, str]:
            return {"status": "ok"}


class NoopRouter(Router):
    """Router used to validate APIRouter construction details."""

    def _register_routes(self) -> None:
        return None


def test_router_create_calls_register_routes_once() -> None:
    TrackingRouter.register_calls = 0

    router = TrackingRouter.create(prefix="/tracking", tags=["tracking"])

    assert isinstance(router, APIRouter)
    assert TrackingRouter.register_calls == 1

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/tracking/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_router_create_converts_tags_to_list_and_applies_kwargs() -> None:
    tags: Sequence[str] = ("alpha", "beta")

    router = NoopRouter.create(prefix="/noop", tags=tags, deprecated=True)

    assert isinstance(router, APIRouter)
    assert router.tags == ["alpha", "beta"]
    assert router.prefix == "/noop"
    assert router.deprecated is True
