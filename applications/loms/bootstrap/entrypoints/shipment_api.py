"""
Shipment BC - Standalone API Entrypoint.

Run independently: uv run uvicorn loms.bootstrap.entrypoints.shipment_api:app --port 8001
"""

from fastapi import FastAPI

from loms.bootstrap.registry import ModuleSpec, ModuleRegistry
from loms.bootstrap.wiring import build_runtime, DictContainer


def create_shipment_app() -> FastAPI:
    """Create FastAPI app for Shipment BC only."""
    from loms.shared.infra.module import InfraModule
    from loms.contexts.shipment.module import ShipmentModule

    # Only register infra + shipment modules
    registry = ModuleRegistry([
        ModuleSpec(name="infra", factory=lambda: InfraModule(), requires=()),
        ModuleSpec(name="shipment", factory=lambda: ShipmentModule(), requires=("infra",)),
    ])

    runtime = build_runtime(registry=registry)

    app = FastAPI(
        title="LOMS Shipment Service",
        version="1.0.0",
        description="Shipment Bounded Context - Standalone",
    )

    container = runtime.container

    # Register shipment router
    try:
        shipment_router = container.get("shipment.router")
        app.include_router(shipment_router, prefix="/api/v1", tags=["shipment"])
    except KeyError:
        pass

    # Health endpoints
    from loms.shared.platform.runtime.health.router import router as health_router
    app.include_router(health_router)

    # App state
    app.state.container = container
    app.state.runtime = runtime
    app.state.service_name = "loms-shipment"
    app.state.contracts = {
        "state_machines": _DummyStateMachine(),
        "schemas": _DummySchemaValidator(),
    }

    return app


class _DummyStateMachine:
    def validate(self, entity: str, current_state: str, action: str) -> None:
        pass


class _DummySchemaValidator:
    def validate_envelope(self, envelope: dict) -> None:
        pass


app = create_shipment_app()
