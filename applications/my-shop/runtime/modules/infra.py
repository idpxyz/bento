"""Infrastructure module for my-shop.

Provides core infrastructure services:
- Database session factory
- Cache
- Message bus
- Outbox projector
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory
from bento.adapters.messaging.inprocess import InProcessMessageBus
from bento.infrastructure.projection.projector import OutboxProjector
from bento.runtime import BentoModule

if TYPE_CHECKING:
    from bento.runtime import BentoContainer

logger = logging.getLogger(__name__)


class InfraModule(BentoModule):
    """Infrastructure module providing core services."""

    name = "infra"

    def __init__(self) -> None:
        super().__init__()
        self._projector_task: asyncio.Task | None = None
        self._projection_session: Any = None

    async def on_register(self, container: "BentoContainer") -> None:
        """Register infrastructure services."""
        # Note: db.session_factory is set by BentoRuntime's database manager
        # during build_async(), so we don't try to access it here.
        # It will be available during on_startup().

        # Message bus
        bus = InProcessMessageBus(source="my-shop")
        container.set("messaging.bus", bus)

        # Cache
        cache = await CacheFactory.create(
            CacheConfig(
                backend=CacheBackend.MEMORY,
                ttl=300,
            )
        )
        container.set("cache", cache)

        logger.info("Infrastructure services registered")

    async def on_startup(self, container: "BentoContainer") -> None:
        """Start infrastructure services."""
        bus: InProcessMessageBus = container.get("messaging.bus")
        session_factory = container.get("db.session_factory")

        # Create projector
        projector = OutboxProjector(
            session_factory=session_factory,
            message_bus=bus,
            tenant_id="default",
        )
        container.set("messaging.projector", projector)

        # Start bus
        await bus.start()

        # Start projector in background
        self._projector_task = asyncio.create_task(projector.run_forever())

        logger.info("Infrastructure services started")

    async def on_shutdown(self, container: "BentoContainer") -> None:
        """Stop infrastructure services."""
        # Stop projector
        projector = container.get("messaging.projector", None)
        if projector:
            await projector.stop()

        if self._projector_task:
            self._projector_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._projector_task

        # Close projection session
        if self._projection_session:
            await self._projection_session.close()

        # Stop bus
        bus = container.get("messaging.bus", None)
        if bus:
            await bus.stop()

        logger.info("Infrastructure services stopped")
