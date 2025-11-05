"""Core module - fundamental building blocks.

This module provides core utilities and exception handling for the Bento framework.
"""

# from bento.core.clock import Clock, SystemClock  # Not yet implemented
from bento.core.error_codes import CommonErrors, RepositoryErrors
from bento.core.error_handler import get_error_responses_schema, register_exception_handlers
from bento.core.errors import (
    ApplicationError,
    ApplicationException,
    BentoException,
    DomainError,
    DomainException,
    ErrorCategory,
    ErrorCode,
    InfraError,
    InfrastructureException,
    InterfaceException,
)
from bento.core.guard import require
from bento.core.ids import ID, EntityId
from bento.core.result import Err, Ok, Result

__all__ = [
    # Clock (not yet implemented)
    # "Clock",
    # "SystemClock",
    # Errors - New exception system
    "BentoException",
    "DomainException",
    "ApplicationException",
    "InfrastructureException",
    "InterfaceException",
    "ErrorCode",
    "ErrorCategory",
    # Errors - Legacy aliases
    "DomainError",
    "ApplicationError",
    "InfraError",
    # Error codes (framework-level only)
    "CommonErrors",
    "RepositoryErrors",
    # Error handler
    "register_exception_handlers",
    "get_error_responses_schema",
    # Guard
    "require",
    # ID
    "ID",
    "EntityId",
    # Result
    "Result",
    "Ok",
    "Err",
]
