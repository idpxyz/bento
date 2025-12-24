"""FastAPI integration utilities for Bento Framework.

This module provides FastAPI-specific utilities for integrating with Bento's
DDD/Hexagonal architecture, including dependency injection helpers.
"""

from bento.interfaces.fastapi.dependencies import (
    HandlerProtocol,
    create_handler_dependency,
)

__all__ = [
    "create_handler_dependency",
    "HandlerProtocol",
]
