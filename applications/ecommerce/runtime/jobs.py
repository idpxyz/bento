"""E-commerce application background jobs.

Wires OutboxProjector to the in-app MessageBus (OrderEventListener)
so that domain events persisted into the Outbox are published
and dispatched to handlers reliably.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from applications.ecommerce.modules.order.application.event_handlers.event_listener import (
    OrderEventListener,
)
from applications.ecommerce.runtime.composition import async_session_factory, init_db
from bento.infrastructure.projection.projector import OutboxProjector


def create_projector(
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    tenant_id: str = "default",
    batch_size: int = 100,
) -> OutboxProjector:
    sf = session_factory or async_session_factory
    message_bus = OrderEventListener()
    return OutboxProjector(
        session_factory=sf,
        message_bus=message_bus,
        tenant_id=tenant_id,
        batch_size=batch_size,
    )


async def run() -> None:
    """Start background projector loop.

    In production, this would be invoked by the app lifecycle
    (e.g., FastAPI startup or a dedicated worker process).
    """
    await init_db()
    projector = create_projector()
    await projector.run_forever()


async def publish_all_once() -> int:
    """Utility for tests: process and publish all pending Outbox events."""
    await init_db()
    projector = create_projector()
    return await projector.publish_all()
