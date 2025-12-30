"""Shipment Bounded Context - Standalone API.

Run independently: uv run uvicorn loms.bootstrap.entrypoints.shipment_api:app --port 8001
"""
import os
from pathlib import Path

from loms.contexts.shipment.module import ShipmentModule
from loms.shared.infra.module import InfraModule

from bento.application.decorators import set_global_contracts
from bento.runtime import BentoRuntime


def create_shipment_app():
    """Create FastAPI app for Shipment BC only."""
    # Find project root for contracts
    project_root = Path(__file__).parent.parent.parent.parent.parent

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./loms.db")

    runtime = (
        BentoRuntime()
        .with_config(
            service_name="loms-shipment",
            environment=os.getenv("ENVIRONMENT", "local"),
        )
        .with_database(url=database_url)
        .with_contracts(str(project_root / "contracts"))
        .with_modules(InfraModule(), ShipmentModule())
    )

    # Set global contracts for @state_transition decorator
    if runtime._contracts:
        set_global_contracts(runtime._contracts)

    app = runtime.create_fastapi_app(
        title="LOMS Shipment Service",
        version="1.0.0",
        description="Shipment Bounded Context - Standalone",
    )

    app.state.runtime = runtime
    return app


app = create_shipment_app()
