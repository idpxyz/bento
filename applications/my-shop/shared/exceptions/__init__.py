"""Exception handling module - DDD-compliant error responses.

This module provides centralized exception handling for the application,
following Domain-Driven Design principles.

Usage:
    from shared.exceptions import (
        validation_exception_handler,
        response_validation_exception_handler,
        generic_exception_handler,
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
"""

from shared.exceptions.handlers import (
    application_exception_handler,
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)

__all__ = [
    "validation_exception_handler",
    "response_validation_exception_handler",
    "application_exception_handler",
    "generic_exception_handler",
]
