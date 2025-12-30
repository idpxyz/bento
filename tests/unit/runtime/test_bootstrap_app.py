from __future__ import annotations

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from bento.runtime import BentoModule, RuntimeBuilder


class DummyModule(BentoModule):
    name = "dummy"

    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self._events = events
        self._router = APIRouter()

        @self._router.get("/ping")
        async def ping():
            return {"pong": True}

    async def on_startup(self, container):
        self._events.append("startup")

    async def on_shutdown(self, container):
        self._events.append("shutdown")

    def get_routers(self):
        # With prefix to exercise tuple handling
        return [(self._router, "/api/v1")]

    def get_middleware(self):
        return [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]


@pytest.mark.asyncio
async def test_create_fastapi_app_registers_routes_middleware_and_lifecycle():
    events: list[str] = []
    runtime = RuntimeBuilder().with_modules(DummyModule(events)).build_runtime()
    app = runtime.create_fastapi_app(title="Test App")

    with TestClient(app) as client:
        # Router tuple with prefix should be registered
        res = client.get("/api/v1/ping")
        assert res.status_code == 200
        assert res.json() == {"pong": True}

        # Default health endpoint should reflect runtime metadata
        health = client.get("/health")
        assert health.status_code == 200
        payload = health.json()
        assert payload["status"] == "healthy"
        assert "dummy" in payload["modules"]

        # Middleware from module should be attached (reverse order handled by app)
        assert any(m.cls is CORSMiddleware for m in app.user_middleware)

    # Lifespan should invoke startup and shutdown hooks
    assert events == ["startup", "shutdown"]
