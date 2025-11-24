"""my-shop - Main FastAPI application entry point.

This module now delegates application creation to runtime.bootstrap.create_app,
which wires lifespan, middleware, exception handlers and routes.
"""

from config import settings
from runtime.bootstrap import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
