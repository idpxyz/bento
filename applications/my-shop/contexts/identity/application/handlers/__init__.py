"""Event handlers for Identity module."""

from contexts.identity.application.handlers.user_event_handlers import (
    UserCreatedHandler,
    UserDeletedHandler,
    UserEmailChangedHandler,
)

__all__ = [
    "UserCreatedHandler",
    "UserEmailChangedHandler",
    "UserDeletedHandler",
]
