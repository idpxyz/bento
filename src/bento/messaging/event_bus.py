"""Event bus abstractions and in-memory implementation."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Protocol

Handler = Callable[[dict], Awaitable[None]]


class EventBus(Protocol):
    """Protocol describing minimal event bus functionality."""

    async def publish(self, topic: str, payload: dict) -> None: ...

    def subscribe(self, topic: str, handler: Handler) -> None: ...


class InMemoryEventBus:
    """Simple in-memory event bus for development and testing."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Register handler for topic."""
        self._handlers[topic].append(handler)

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish payload to all handlers subscribed to topic."""
        if topic not in self._handlers:
            return

        coroutines = [handler(payload) for handler in self._handlers[topic]]
        if not coroutines:
            return

        await asyncio.gather(*coroutines, return_exceptions=False)

    async def close(self) -> None:
        """Explicit close hook for symmetry with other buses."""
        self._handlers.clear()
