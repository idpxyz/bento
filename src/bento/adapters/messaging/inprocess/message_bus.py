from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from bento.application.ports.message_bus import MessageBus
from bento.domain.domain_event import DomainEvent

logger = logging.getLogger(__name__)


class InProcessMessageBus(MessageBus):
    """In-process implementation of MessageBus.

    - Handlers are invoked within the same event loop/process
    - Supports single and batch publish
    - Tolerates handler failures (logs and continues)
    """

    def __init__(self, *, source: str = "inprocess-bus") -> None:
        self._source = source
        self._running = False
        # event_type_name -> list[handler]
        self._handlers: dict[str, list[Callable[[DomainEvent], Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._running:
                return
            self._running = True
            logger.info("InProcessMessageBus[%s] started", self._source)

    async def stop(self) -> None:
        async with self._lock:
            if not self._running:
                return
            self._running = False
            logger.info("InProcessMessageBus[%s] stopped", self._source)

    async def publish(self, event: DomainEvent | list[DomainEvent]) -> None:
        if not self._running:
            raise RuntimeError("MessageBus is not started. Call start() first.")

        events: list[DomainEvent] = event if isinstance(event, list) else [event]

        for ev in events:
            et = self._event_type_name(ev)
            handlers = list(self._handlers.get(et, []))
            if not handlers:
                # No subscribers is still a successful publish (like typical MQ)
                logger.debug("No handlers for event type %s", et)
                continue

            for handler in handlers:
                try:
                    res = handler(ev)
                    if asyncio.iscoroutine(res):
                        await res  # type: ignore[arg-type]
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Handler error for %s on bus[%s]: %s", et, self._source, exc, exc_info=True
                    )
                    # Continue to next handler/event

    async def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], Any] | Callable[[DomainEvent], Awaitable[Any]],
    ) -> None:
        et_name = self._event_type_name_from_cls(event_type)
        self._handlers[et_name].append(handler)
        logger.info("Subscribed handler to %s on bus[%s]", et_name, self._source)

    async def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], Any] | Callable[[DomainEvent], Awaitable[Any]],
    ) -> None:
        et_name = self._event_type_name_from_cls(event_type)
        try:
            self._handlers[et_name].remove(handler)
            logger.info("Unsubscribed handler from %s on bus[%s]", et_name, self._source)
        except ValueError:
            pass

    @staticmethod
    def _event_type_name(event: DomainEvent) -> str:
        return f"{event.__class__.__module__}.{event.__class__.__name__}"

    @staticmethod
    def _event_type_name_from_cls(event_type: type[DomainEvent]) -> str:
        return f"{event_type.__module__}.{event_type.__name__}"
