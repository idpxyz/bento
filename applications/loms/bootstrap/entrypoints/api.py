"""FastAPI HTTP API Entrypoint.

This is the main entry point for the HTTP API server.
It uses BentoRuntime for consistent application bootstrap.
"""
import os
from pathlib import Path

from bento.application.decorators import set_global_contracts
from bento.runtime import BentoRuntime

from loms.contexts.leg.module import LegModule
from loms.contexts.shipment.module import ShipmentModule
from loms.shared.infra.module import InfraModule

# Global runtime instance for dependency injection
_runtime: BentoRuntime | None = None


def get_runtime() -> BentoRuntime:
    """Get the global runtime instance."""
    if _runtime is None:
        raise RuntimeError("Runtime not initialized. Call create_app() first.")
    return _runtime


def create_app():
    """Create and configure the FastAPI application via BentoRuntime."""
    global _runtime

    # Find project root for contracts
    project_root = Path(__file__).parent.parent.parent.parent.parent

    # Database URL from environment or default
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./loms.db",
    )

    runtime = (
        BentoRuntime()
        .with_config(
            service_name="loms-platform",
            environment=os.getenv("ENVIRONMENT", "local"),
        )
        .with_database(url=database_url)
        .with_contracts(str(project_root / "contracts"))
        .with_modules(
            InfraModule(),
            ShipmentModule(),
            LegModule(),
        )
    )

    # Store runtime globally for DI
    _runtime = runtime

    # Set global contracts for @state_transition decorator
    if runtime._contracts:
        set_global_contracts(runtime._contracts)

    app = runtime.create_fastapi_app(
        title="LOMS Platform",
        version="1.0.0",
        description="Logistics Order Management System",
    )

    # Store runtime in app state for route access
    app.state.runtime = runtime

    return app


# For uvicorn: uvicorn loms.bootstrap.entrypoints.api:app
app = create_app()
