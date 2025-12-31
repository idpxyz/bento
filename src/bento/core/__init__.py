"""Core module - fundamental building blocks.

This module provides core utilities and exception handling for the Bento framework.

Exception System:
    Exceptions are driven by contracts (reason codes from JSON files):

    ```python
    from bento.core import DomainException
    raise DomainException(reason_code="STATE_CONFLICT", order_id="123")
    # Automatically gets: http_status=409, message from contracts
    ```
"""

# from bento.core.clock import Clock, SystemClock  # Not yet implemented
from bento.core.exception_handler import get_exception_responses_schema, register_exception_handlers

# Exception system (contract-based)
from bento.core.exceptions import (
    ApplicationException,
    BentoException,
    DomainException,
    ExceptionCategory,
    InfrastructureException,
    InterfaceException,
    get_global_catalog,
    get_global_message_renderer,
    set_global_catalog,
    set_global_message_renderer,
)

# i18n system (optional)
from bento.core.i18n import ILocaleResolver, IMessageRenderer, LocaleContext
from bento.core.guard import require
from bento.core.ids import ID, EntityId
from bento.core.result import Err, Ok, Result

__all__ = [
    # Exceptions - Contract-based system
    "BentoException",
    "DomainException",
    "ApplicationException",
    "InfrastructureException",
    "InterfaceException",
    "ExceptionCategory",
    "set_global_catalog",
    "get_global_catalog",
    "set_global_message_renderer",
    "get_global_message_renderer",
    # i18n - Optional internationalization support
    "IMessageRenderer",
    "ILocaleResolver",
    "LocaleContext",
    # Exception handler
    "register_exception_handlers",
    "get_exception_responses_schema",
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
