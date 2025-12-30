"""Tests for tenant middleware."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

from bento.multitenancy import HeaderTenantResolver, TenantContext


@pytest.fixture(autouse=True)
def clear_context():
    """Clear tenant context before and after each test."""
    TenantContext.clear()
    yield
    TenantContext.clear()


class TestAddTenantMiddleware:
    """Tests for add_tenant_middleware function."""

    async def test_sets_tenant_context_from_resolver(self):
        """Middleware should set TenantContext from resolver."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        from bento.multitenancy import add_tenant_middleware

        add_tenant_middleware(
            app,
            resolver=HeaderTenantResolver(),
            require_tenant=False,
        )

        captured_tenant = None

        @app.get("/test")
        async def test_endpoint():
            nonlocal captured_tenant
            captured_tenant = TenantContext.get()
            return {"tenant": captured_tenant}

        client = TestClient(app)
        response = client.get("/test", headers={"X-Tenant-ID": "tenant-123"})

        assert response.status_code == 200
        assert captured_tenant == "tenant-123"

    async def test_returns_400_when_tenant_required_but_missing(self):
        """Middleware should return 400 when tenant required but missing."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        from bento.multitenancy import add_tenant_middleware

        add_tenant_middleware(
            app,
            resolver=HeaderTenantResolver(),
            require_tenant=True,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 400
        assert response.json()["reason_code"] == "TENANT_REQUIRED"

    async def test_excludes_paths(self):
        """Middleware should skip excluded paths."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        from bento.multitenancy import add_tenant_middleware

        add_tenant_middleware(
            app,
            resolver=HeaderTenantResolver(),
            require_tenant=True,
            exclude_paths=["/health"],
        )

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/api")
        async def api():
            return {"ok": True}

        client = TestClient(app)

        # Health should work without tenant
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # API should require tenant
        api_response = client.get("/api")
        assert api_response.status_code == 400

    async def test_clears_context_after_request(self):
        """Middleware should clear TenantContext after request."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        from bento.multitenancy import add_tenant_middleware

        add_tenant_middleware(
            app,
            resolver=HeaderTenantResolver(),
            require_tenant=False,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"tenant": TenantContext.get()}

        client = TestClient(app)
        client.get("/test", headers={"X-Tenant-ID": "tenant-123"})

        # Context should be cleared after request
        assert TenantContext.get() is None
