"""
FastAPI HTTP API Entrypoint.

This is the main entry point for the HTTP API server.
It uses the bootstrap wiring to build a consistent runtime.
"""
import os
from pathlib import Path
from fastapi import FastAPI

from loms.bootstrap.wiring import build_runtime


def create_app() -> FastAPI:
    """Create and configure the FastAPI application via bootstrap wiring."""
    runtime = build_runtime()

    app = FastAPI(
        title="LOMS Platform",
        version="1.0.0",
        description="Logistics Order Management System",
    )

    # Register routers from modules
    container = runtime.container

    # Shipment router
    try:
        shipment_router = container.get("shipment.router")
        app.include_router(shipment_router, prefix="/api/v1", tags=["shipment"])
    except KeyError:
        pass  # Module not registered

    # Leg router
    try:
        leg_router = container.get("leg.router")
        app.include_router(leg_router, prefix="/api/v1", tags=["leg"])
    except KeyError:
        pass  # Module not registered

    # Health endpoints
    from loms.shared.platform.runtime.health.router import router as health_router
    app.include_router(health_router)

    # Load contracts from YAML files
    contracts = _load_contracts()

    # Store container in app state for dependency injection
    app.state.container = container
    app.state.runtime = runtime
    app.state.service_name = "loms-platform"
    app.state.contracts = contracts

    return app


def _load_contracts() -> dict:
    """Load contracts from YAML/JSON files using ContractLoader."""
    try:
        from loms.shared.contracts.loader import ContractLoader
        # Find project root (where contracts/ directory is)
        project_root = Path(__file__).parent.parent.parent.parent.parent
        return ContractLoader.load_from_dir(str(project_root))
    except Exception as e:
        # Fallback to dummy implementations if contracts not available
        print(f"[WARN] Could not load contracts: {e}. Using fallback.")
        return {
            "state_machines": _DummyStateMachine(),
            "schemas": None,
            "reason_codes": None,
            "routing": None,
        }


class _DummyStateMachine:
    """Fallback state machine when contracts are not loaded."""
    def validate(self, aggregate: str, current_state: str, command: str) -> None:
        pass  # Allow all transitions


# For uvicorn: uvicorn loms.bootstrap.entrypoints.api:app
app = create_app()
