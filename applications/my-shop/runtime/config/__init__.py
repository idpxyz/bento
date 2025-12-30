"""Runtime Configuration Package.

This package contains all configuration modules for the my-shop application:
- runtime_config: Runtime and module configuration
- middleware_config: Middleware stack configuration
- app_config: Routes, exception handlers, and OpenAPI configuration
"""

from runtime.config.app_config import (
    configure_exception_handlers,
    configure_openapi,
    configure_routes,
)
from runtime.config.middleware_config import configure_middleware
from runtime.config.runtime_config import build_runtime, get_runtime

__all__ = [
    # Runtime configuration
    "build_runtime",
    "get_runtime",
    # Middleware configuration
    "configure_middleware",
    # App configuration
    "configure_exception_handlers",
    "configure_routes",
    "configure_openapi",
]
