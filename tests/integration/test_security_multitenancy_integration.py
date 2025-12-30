"""Integration tests for Security and Multi-tenancy middleware."""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from shared.auth import StubAuthenticator

from bento.core.exceptions import DomainException
from bento.multitenancy import HeaderTenantResolver, add_tenant_middleware
from bento.runtime.integrations.security import setup_security
from bento.runtime.middleware import RequestIDMiddleware
from bento.security import SecurityContext


@pytest.fixture
def app():
    """Create a test FastAPI app with security and tenant middleware."""
    app = FastAPI()

    # Exception handler for DomainException
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request, exc):
        return JSONResponse(
            status_code=400,
            content={
                "reason_code": exc.reason_code,
                "message": str(exc),
            },
        )

    # Setup security middleware
    setup_security(
        app,
        authenticator=StubAuthenticator(),
        require_auth=False,
        exclude_paths=["/health"],
    )

    # Setup tenant middleware with auto-sync
    add_tenant_middleware(
        app,
        resolver=HeaderTenantResolver(header_name="X-Tenant-ID"),
        require_tenant=False,
        exclude_paths=["/health"],
        sync_to_security_context=True,
    )

    # Add request ID middleware
    app.add_middleware(
        RequestIDMiddleware,
        header_name="X-Request-ID",
    )

    # Test endpoints
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/user-info")
    async def user_info():
        """Get current user info."""
        user = SecurityContext.get_user()
        tenant_id = SecurityContext.get_tenant()
        return {
            "user": user.id if user else None,
            "tenant": tenant_id,
        }

    @app.get("/require-user")
    async def require_user():
        """Endpoint that requires user."""
        user = SecurityContext.require_user()
        return {"user": user.id}

    @app.get("/require-tenant")
    async def require_tenant():
        """Endpoint that requires tenant."""
        tenant_id = SecurityContext.require_tenant()
        return {"tenant": tenant_id}

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestSecurityMultitenancyIntegration:
    """Test security and multi-tenancy integration."""

    def test_user_and_tenant_both_available(self, client):
        """Test that user and tenant are both available."""
        response = client.get(
            "/user-info",
            headers={"X-Tenant-ID": "tenant-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"] == "demo-user"
        assert data["tenant"] == "tenant-1"

    def test_user_without_tenant(self, client):
        """Test user available without tenant."""
        response = client.get("/user-info")

        assert response.status_code == 200
        data = response.json()
        assert data["user"] == "demo-user"
        assert data["tenant"] is None

    def test_require_user_succeeds(self, client):
        """Test require_user succeeds with authenticated user."""
        response = client.get("/require-user")

        assert response.status_code == 200
        data = response.json()
        assert data["user"] == "demo-user"

    def test_require_tenant_fails_without_tenant(self, client):
        """Test require_tenant fails without tenant."""
        response = client.get("/require-tenant")

        assert response.status_code == 400
        data = response.json()
        assert data["reason_code"] == "TENANT_REQUIRED"

    def test_require_tenant_succeeds_with_tenant(self, client):
        """Test require_tenant succeeds with tenant."""
        response = client.get(
            "/require-tenant",
            headers={"X-Tenant-ID": "tenant-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant"] == "tenant-1"

    def test_multiple_requests_with_different_tenants(self, client):
        """Test multiple requests with different tenants."""
        # Request 1
        response1 = client.get(
            "/user-info",
            headers={"X-Tenant-ID": "tenant-1"},
        )
        assert response1.json()["tenant"] == "tenant-1"

        # Request 2
        response2 = client.get(
            "/user-info",
            headers={"X-Tenant-ID": "tenant-2"},
        )
        assert response2.json()["tenant"] == "tenant-2"

        # Request 3 without tenant
        response3 = client.get("/user-info")
        assert response3.json()["tenant"] is None

    def test_health_endpoint_excluded(self, client):
        """Test health endpoint is excluded from middleware."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_context_isolation_between_requests(self, client):
        """Test context is isolated between requests."""
        # First request with tenant
        response1 = client.get(
            "/user-info",
            headers={"X-Tenant-ID": "tenant-1"},
        )
        assert response1.json()["tenant"] == "tenant-1"

        # Second request without tenant - should not have tenant from first request
        response2 = client.get("/user-info")
        assert response2.json()["tenant"] is None

        # Third request with different tenant
        response3 = client.get(
            "/user-info",
            headers={"X-Tenant-ID": "tenant-2"},
        )
        assert response3.json()["tenant"] == "tenant-2"
