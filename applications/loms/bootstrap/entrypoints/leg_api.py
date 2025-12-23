"""
Leg BC - Standalone API Entrypoint.

Run independently: uv run uvicorn loms.bootstrap.entrypoints.leg_api:app --port 8002
"""

from fastapi import FastAPI

from loms.bootstrap.registry import ModuleSpec, ModuleRegistry
from loms.bootstrap.wiring import build_runtime


def create_leg_app() -> FastAPI:
    """Create FastAPI app for Leg BC only."""
    from loms.shared.infra.module import InfraModule
    from loms.contexts.leg.module import LegModule

    # Only register infra + leg modules
    registry = ModuleRegistry([
        ModuleSpec(name="infra", factory=lambda: InfraModule(), requires=()),
        ModuleSpec(name="leg", factory=lambda: LegModule(), requires=("infra",)),
    ])

    runtime = build_runtime(registry=registry)

    app = FastAPI(
        title="LOMS Leg Service",
        version="1.0.0",
        description="Leg Bounded Context - Standalone",
    )

    container = runtime.container

    # Register leg router
    try:
        leg_router = container.get("leg.router")
        app.include_router(leg_router, prefix="/api/v1", tags=["leg"])
    except KeyError:
        pass

    # Health endpoints
    from loms.shared.platform.runtime.health.router import router as health_router
    app.include_router(health_router)

    # App state
    app.state.container = container
    app.state.runtime = runtime
    app.state.service_name = "loms-leg"

    return app


app = create_leg_app()
