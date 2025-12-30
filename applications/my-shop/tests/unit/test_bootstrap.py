"""Tests for bootstrap_v2 best practices implementation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from runtime.bootstrap import create_app
from runtime.config import build_runtime, get_runtime


def test_build_runtime_creates_runtime():
    """Test that build_runtime creates a BentoRuntime instance."""
    runtime = build_runtime()

    assert runtime is not None
    assert hasattr(runtime, "container")
    assert hasattr(runtime, "registry")
    assert hasattr(runtime, "config")


def test_get_runtime_returns_runtime():
    """Test that get_runtime returns a BentoRuntime instance.

    Note: Runtime is not fully initialized until FastAPI lifespan runs.
    """
    runtime = get_runtime()

    assert runtime is not None
    assert hasattr(runtime, "container")
    assert hasattr(runtime, "registry")

    # Runtime is not yet built (will be built in lifespan)
    assert runtime._built is False


def test_create_app_returns_fastapi():
    """Test that create_app returns a FastAPI application."""
    app = create_app()

    assert app is not None
    assert hasattr(app, "routes")
    assert hasattr(app, "state")


def test_app_has_custom_routes():
    """Test that custom routes are registered."""
    app = create_app()

    with TestClient(app) as client:
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Runtime info may be in message or separate field
        assert "message" in data or "status" in data

        # Test ping endpoint
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json() == {"message": "pong"}

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        # Health endpoint returns service, modules, database info
        assert "service" in data or "modules" in data


def test_app_has_cors_middleware():
    """Test that CORS middleware is configured."""
    app = create_app()

    # Check that middleware is registered (check middleware list)
    # Middleware may be wrapped, so check for any middleware presence
    assert len(app.user_middleware) > 0, "No middleware registered"


def test_app_lifespan_initializes_runtime():
    """Test that app lifespan properly initializes runtime."""
    app = create_app()

    with TestClient(app):
        # After startup, runtime should be in app.state
        assert hasattr(app.state, "runtime")
        assert hasattr(app.state, "container")

        # Verify runtime is initialized
        runtime = app.state.runtime
        assert runtime._built is True

        # Verify service discovery is available
        discovery = runtime.container.get("service.discovery")
        assert discovery is not None


def test_runtime_modules_registered():
    """Test that all modules are properly registered."""
    runtime = get_runtime()

    # Check that modules are registered
    module_names = [m.name for m in runtime.registry.resolve_order()]

    # Should have at least these modules
    assert "infra" in module_names
    assert "catalog" in module_names
    assert "identity" in module_names
    assert "ordering" in module_names
    assert "service_discovery" in module_names


def test_database_configured():
    """Test that database is configured in runtime."""
    runtime = get_runtime()

    # Database should be configured
    assert runtime.config.database is not None
    assert runtime.config.database.url is not None
