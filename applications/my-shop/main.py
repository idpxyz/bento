"""my-shop - Main FastAPI application entry point.

This module delegates application creation to runtime.bootstrap_v2.create_app,
which uses Bento Runtime with proper lifespan management.
"""

from config import settings
from runtime.bootstrap_v2 import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
