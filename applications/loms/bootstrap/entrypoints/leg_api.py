"""
Leg BC - Standalone API Entrypoint.

Run independently: uv run uvicorn loms.bootstrap.entrypoints.leg_api:app --port 8002
"""
import os

from loms.contexts.leg.module import LegModule
from loms.shared.infra.module import InfraModule

from bento.runtime import BentoRuntime


def create_leg_app():
    """Create FastAPI app for Leg BC only."""
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./loms.db")

    runtime = (
        BentoRuntime()
        .with_config(
            service_name="loms-leg",
            environment=os.getenv("ENVIRONMENT", "local"),
        )
        .with_database(url=database_url)
        .with_modules(InfraModule(), LegModule())
    )

    app = runtime.create_fastapi_app(
        title="LOMS Leg Service",
        version="1.0.0",
        description="Leg Bounded Context - Standalone",
    )

    app.state.runtime = runtime
    return app


app = create_leg_app()
