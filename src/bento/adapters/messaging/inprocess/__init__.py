"""In-process MessageBus adapter.

Provides a lightweight MessageBus implementation that delivers events to
subscribed handlers within the same process. Useful when bounded contexts
are deployed together without an external broker.
"""

from .message_bus import InProcessMessageBus

__all__ = ["InProcessMessageBus"]
