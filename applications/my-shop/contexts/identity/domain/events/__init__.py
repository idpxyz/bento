"""Identity domain events."""

from contexts.identity.domain.events.user_events import (
    UserCreated,
    UserDeleted,
    UserEmailChanged,
    UserUpdated,
)

__all__ = [
    "UserCreated",
    "UserUpdated",
    "UserDeleted",
    "UserEmailChanged",
]
