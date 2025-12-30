"""Messaging manager for event bus and outbox."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class MessagingManager:
    """Manages messaging infrastructure (event bus, outbox)."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize messaging manager.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    def setup(self) -> None:
        """Setup event bus and outbox."""
        # Setup event bus if not provided
        if not self.runtime._event_bus:
            try:
                from bento.messaging.event_bus import InMemoryEventBus
                self.runtime._event_bus = InMemoryEventBus()
                logger.info("Event bus configured: InMemoryEventBus")
            except ImportError:
                logger.warning("Event bus not available, continuing without event bus")
                return

        self.runtime.container.set("event_bus", self.runtime._event_bus)
        logger.debug("Messaging infrastructure ready")

    async def cleanup(self) -> None:
        """Cleanup messaging resources."""
        if self.runtime._event_bus:
            if hasattr(self.runtime._event_bus, "close"):
                await self.runtime._event_bus.close()
                logger.info("Event bus closed")
