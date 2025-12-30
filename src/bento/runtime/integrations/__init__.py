"""Integration modules for Bento Runtime.

This package contains various integration modules that connect
the runtime with different frameworks and tools.

Available integrations:
- setup_bento_openapi: FastAPI OpenAPI customization
- setup_security: Security middleware setup
"""

from bento.runtime.integrations.di import DIIntegration
from bento.runtime.integrations.fastapi import FastAPIIntegration
from bento.runtime.integrations.fastapi_openapi import setup_bento_openapi
from bento.runtime.integrations.modules import ModuleManager
from bento.runtime.integrations.performance import PerformanceMonitor
from bento.runtime.integrations.security import setup_security

__all__ = [
    "DIIntegration",
    "FastAPIIntegration",
    "ModuleManager",
    "PerformanceMonitor",
    "setup_bento_openapi",
    "setup_security",
]
