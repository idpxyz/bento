"""Integration modules for Bento Runtime.

This package contains various integration modules that connect
the runtime with different frameworks and tools.
"""

from bento.runtime.integrations.di import DIIntegration
from bento.runtime.integrations.fastapi import FastAPIIntegration
from bento.runtime.integrations.fastapi_openapi import setup_bento_openapi
from bento.runtime.integrations.modules import ModuleManager
from bento.runtime.integrations.performance import PerformanceMonitor

__all__ = [
    "DIIntegration",
    "FastAPIIntegration",
    "ModuleManager",
    "PerformanceMonitor",
    "setup_bento_openapi",
]
