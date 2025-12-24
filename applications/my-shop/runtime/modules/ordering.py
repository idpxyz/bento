"""Ordering module for my-shop.

Provides ordering context:
- Order repository
- Event handlers (projections)
- API routers
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bento.runtime import BentoModule

if TYPE_CHECKING:
    from bento.runtime import BentoContainer

logger = logging.getLogger(__name__)


class OrderingModule(BentoModule):
    """Ordering bounded context module."""

    name = "ordering"
    requires = ["infra", "catalog"]
    scan_packages = [
        "contexts.ordering.infrastructure.repositories.order_repository_impl",
        "contexts.ordering.infrastructure.adapters.services.product_catalog_adapter",
    ]

    async def on_register(self, container: "BentoContainer") -> None:
        """Register ordering services."""
        from contexts.ordering.infrastructure.repositories.order_repository_impl import (
            OrderRepository,
        )

        container.set_factory("ordering.order_repository", OrderRepository)

        logger.info("Ordering services registered")

    async def on_startup(self, container: "BentoContainer") -> None:
        """Register event handlers for projections."""
        from contexts.ordering.application.projections.order_projection import (
            OrderProjection,
        )
        from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent
        from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent
        from contexts.ordering.domain.events.ordershipped_event import OrderShippedEvent

        bus = container.get("messaging.bus")
        session_factory = container.get("db.session_factory")

        # Create projection with its own session
        session = session_factory()
        order_projection = OrderProjection(session)
        container.set("ordering.projection", order_projection)
        container.set("ordering.projection_session", session)

        # Subscribe to events
        await bus.subscribe(OrderCreatedEvent, order_projection.handle_order_created)
        await bus.subscribe(OrderPaidEvent, order_projection.handle_order_paid)
        await bus.subscribe(OrderShippedEvent, order_projection.handle_order_shipped)

        logger.info("Ordering event handlers registered")

    async def on_shutdown(self, container: "BentoContainer") -> None:
        """Clean up ordering resources."""
        session = container.get("ordering.projection_session", None)
        if session is not None:
            await session.close()  # type: ignore[union-attr]

        logger.info("Ordering resources cleaned up")

    def get_routers(self) -> list:
        """Return ordering API routers with /api/v1 prefix."""
        from fastapi import APIRouter
        from contexts.ordering.interfaces import register_routes

        router = APIRouter(prefix="/api/v1")
        register_routes(router)
        return [router]
