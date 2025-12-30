"""FastAPI integration utilities for Bento Framework.

This module provides FastAPI-specific utilities for integrating with Bento's
DDD/Hexagonal architecture, including dependency injection helpers.
"""

from bento.core.exception_handler import register_exception_handlers

# Re-export core exceptions for convenience
from bento.core.exceptions import (
    ApplicationException,
    BentoException,
    DomainException,
    InfrastructureException,
    InterfaceException,
)
from bento.interfaces.fastapi.dependencies import (
    HandlerProtocol,
    create_handler_dependency,
    get_uow_from_runtime,
    handler_dependency,
)

__all__ = [
    "create_handler_dependency",
    "handler_dependency",
    "get_uow_from_runtime",
    "HandlerProtocol",
    "BentoException",
    "DomainException",
    "ApplicationException",
    "InfrastructureException",
    "InterfaceException",
    "register_exception_handlers",
]
