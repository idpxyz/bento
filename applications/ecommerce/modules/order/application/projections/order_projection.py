"""Order projection - synchronizes write model to read model.

Listens to domain events and updates the read model accordingly.
This is the CQRS "projection" pattern.
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from applications.ecommerce.modules.order.domain.events import (
    OrderCancelled,
    OrderCreated,
    OrderPaid,
)
from applications.ecommerce.modules.order.persistence.models.order_model import (
    OrderModel,
)
from applications.ecommerce.modules.order.persistence.models.order_read_model import (
    OrderItemReadModel,
    OrderReadModel,
)
from bento.core.ids import ID

logger = logging.getLogger(__name__)


class OrderProjection:
    """Projects Order write model to read model.

    Responsibilities:
    1. Listen to domain events (OrderCreated, OrderPaid, etc.)
    2. Update read models based on events
    3. Keep read models in sync with write models

    Pattern: Event-Driven Projection
    - Guarantees eventual consistency
    - Decouples write and read sides
    - Scalable and maintainable
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize projection.

        Args:
            session: Database session for read model updates
        """
        self._session = session

    async def handle_order_created(self, event: OrderCreated) -> None:
        """Project OrderCreated event to read model.

        Args:
            event: Domain event containing order data
        """
        logger.info(f"Projecting OrderCreated event: {event.order_id}")

        # Fetch the write model (source of truth)
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(OrderModel)
            .where(OrderModel.id == event.order_id.value)
            .options(selectinload(OrderModel.items))
        )
        result = await self._session.execute(stmt)
        order_po = result.scalar_one_or_none()

        if not order_po:
            logger.warning(f"Order not found for projection: {event.order_id}")
            return

        # Calculate denormalized fields
        total_amount = sum(item.unit_price * item.quantity for item in order_po.items)
        items_count = len(order_po.items)

        # Create read model
        read_model = OrderReadModel(
            id=order_po.id,
            customer_id=order_po.customer_id,
            status=order_po.status,
            total_amount=total_amount,
            items_count=items_count,
            created_at=order_po.created_at or datetime.now(),
            updated_at=order_po.updated_at or datetime.now(),
            paid_at=None,
            cancelled_at=None,
        )

        self._session.add(read_model)

        # Create item read models
        for item in order_po.items:
            item_read_model = OrderItemReadModel(
                id=item.id,
                order_id=order_po.id,
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.unit_price * item.quantity,
                # Denormalized order info
                customer_id=order_po.customer_id,
                order_status=order_po.status,
                order_created_at=order_po.created_at or datetime.now(),
            )
            self._session.add(item_read_model)

        await self._session.flush()
        logger.info(f"Read model created for order: {event.order_id}")

    async def handle_order_paid(self, event: OrderPaid) -> None:
        """Project OrderPaid event to read model.

        Args:
            event: Domain event
        """
        logger.info(f"Projecting OrderPaid event: {event.order_id}")

        from sqlalchemy import update

        # Update order read model
        stmt = (
            update(OrderReadModel)
            .where(OrderReadModel.id == event.order_id.value)
            .values(
                status="paid",
                paid_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        await self._session.execute(stmt)

        # Update item read models
        stmt = (
            update(OrderItemReadModel)
            .where(OrderItemReadModel.order_id == event.order_id.value)
            .values(order_status="paid")
        )
        await self._session.execute(stmt)

        await self._session.flush()
        logger.info(f"Read model updated for paid order: {event.order_id}")

    async def handle_order_cancelled(self, event: OrderCancelled) -> None:
        """Project OrderCancelled event to read model.

        Args:
            event: Domain event
        """
        logger.info(f"Projecting OrderCancelled event: {event.order_id}")

        from sqlalchemy import update

        # Update order read model
        stmt = (
            update(OrderReadModel)
            .where(OrderReadModel.id == event.order_id.value)
            .values(
                status="cancelled",
                cancelled_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        await self._session.execute(stmt)

        # Update item read models
        stmt = (
            update(OrderItemReadModel)
            .where(OrderItemReadModel.order_id == event.order_id.value)
            .values(order_status="cancelled")
        )
        await self._session.execute(stmt)

        await self._session.flush()
        logger.info(f"Read model updated for cancelled order: {event.order_id}")

    async def rebuild_from_write_model(self, order_id: ID) -> None:
        """Rebuild read model from write model (recovery/sync).

        Useful for:
        - Initial data load
        - Fixing inconsistencies
        - Adding new read models

        Args:
            order_id: Order to rebuild
        """
        logger.info(f"Rebuilding read model for order: {order_id}")

        from sqlalchemy import delete, select
        from sqlalchemy.orm import selectinload

        # Delete existing read models
        await self._session.execute(
            delete(OrderReadModel).where(OrderReadModel.id == order_id.value)
        )
        await self._session.execute(
            delete(OrderItemReadModel).where(OrderItemReadModel.order_id == order_id.value)
        )

        # Recreate from write model
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id.value)
            .options(selectinload(OrderModel.items))
        )
        result = await self._session.execute(stmt)
        order_po = result.scalar_one_or_none()

        if order_po:
            # Simulate OrderCreated event
            from applications.ecommerce.modules.order.domain.events import OrderCreated

            event = OrderCreated(order_id=ID(order_po.id), customer_id=ID(order_po.customer_id))
            await self.handle_order_created(event)

            # Apply status-specific events
            if order_po.status == "paid":
                from applications.ecommerce.modules.order.domain.events import OrderPaid

                event = OrderPaid(order_id=ID(order_po.id))
                await self.handle_order_paid(event)
            elif order_po.status == "cancelled":
                from applications.ecommerce.modules.order.domain.events import OrderCancelled

                event = OrderCancelled(order_id=ID(order_po.id), reason="Rebuilt")
                await self.handle_order_cancelled(event)

        logger.info(f"Read model rebuilt for order: {order_id}")
