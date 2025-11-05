"""Order repository implementation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applications.ecommerce.modules.order.domain.order import Order, OrderItem
from applications.ecommerce.modules.order.domain.order_status import OrderStatus
from applications.ecommerce.persistence.models import OrderItemModel, OrderModel
from bento.core.ids import ID
from bento.domain.ports.repository import Repository as IRepository


class OrderRepository(IRepository[Order, ID]):
    """Order repository implementation.

    Simple repository that directly maps between Order (domain) and OrderModel (PO).

    Note: This is a simplified implementation for demonstration.
    In production, consider using RepositoryAdapter with a proper Mapper.

    Example:
        ```python
        session = get_session()
        order_repo = OrderRepository(session)

        order = await order_repo.find_by_id(order_id)
        await order_repo.save(order)
        ```
    """

    def __init__(self, session: AsyncSession, uow=None) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
            uow: Optional Unit of Work for automatic event tracking
        """
        self._session = session
        self._uow = uow

    async def find_by_id(self, id: ID) -> Order | None:
        """Find order by ID.

        Args:
            id: Order identifier

        Returns:
            Order if found, None otherwise
        """
        import logging

        from sqlalchemy.orm import selectinload

        logger = logging.getLogger(__name__)

        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == id.value)
        )
        order_model = result.scalar_one_or_none()

        if not order_model:
            return None

        # Debug: log items count
        logger.info(f"Loading order {id.value}, found {len(order_model.items)} items in DB")

        order = self._to_domain(order_model)
        logger.info(f"Converted to domain, order has {len(order.items)} items")

        return order

    async def save(self, entity: Order) -> Order:
        """Save order (create or update).

        Args:
            entity: Order to save

        Returns:
            Saved order
        """
        from sqlalchemy.orm import selectinload

        # Check if exists (with items loaded)
        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == entity.id.value)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing order
            existing.customer_id = entity.customer_id.value
            existing.status = entity.status.value
            existing.paid_at = entity.paid_at
            existing.cancelled_at = entity.cancelled_at

            # Update items: delete old, add new
            # Clear existing items
            for item_model in list(existing.items):
                await self._session.delete(item_model)

            # Add new items
            for item in entity.items:
                # Get item ID - handle both EntityId and ID types
                item_id = item.id.value if hasattr(item.id, "value") else str(item.id)

                item_model = OrderItemModel(
                    id=item_id,
                    order_id=entity.id.value,
                    product_id=item.product_id.value
                    if hasattr(item.product_id, "value")
                    else str(item.product_id),
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                self._session.add(item_model)

            await self._session.flush()
        else:
            # Create new order
            order_model = self._to_model(entity)
            self._session.add(order_model)

            # Add items
            for item in entity.items:
                # Get item ID - handle both EntityId and ID types
                item_id = item.id.value if hasattr(item.id, "value") else str(item.id)

                item_model = OrderItemModel(
                    id=item_id,
                    order_id=entity.id.value,
                    product_id=item.product_id.value
                    if hasattr(item.product_id, "value")
                    else str(item.product_id),
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                self._session.add(item_model)

            # Flush to ensure items are saved
            await self._session.flush()

            # Verify items were added
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Created order {entity.id.value} with {len(entity.items)} items")

        # ✅ Automatically track aggregate for event collection
        if self._uow and hasattr(self._uow, "track"):
            self._uow.track(entity)
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Automatically tracked order {entity.id.value} for event collection")

        return entity

    async def delete(self, entity: Order) -> None:
        """Delete order.

        Args:
            entity: Order to delete
        """
        order_model = await self._session.get(OrderModel, entity.id.value)
        if order_model:
            await self._session.delete(order_model)

    async def find_all(self) -> list[Order]:
        """Find all orders.

        Returns:
            List of all orders
        """
        from sqlalchemy.orm import selectinload

        result = await self._session.execute(
            select(OrderModel).options(selectinload(OrderModel.items))
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def exists(self, id: ID) -> bool:
        """Check if order exists.

        Args:
            id: Order identifier

        Returns:
            True if exists, False otherwise
        """
        result = await self._session.execute(select(OrderModel).where(OrderModel.id == id.value))
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """Count total orders.

        Returns:
            Total count
        """
        from sqlalchemy import func

        result = await self._session.execute(select(func.count()).select_from(OrderModel))
        return result.scalar() or 0

    def _to_domain(self, model: OrderModel) -> Order:
        """Convert OrderModel to Order domain entity."""
        # Create order with basic info
        order = Order(
            order_id=ID(model.id),
            customer_id=ID(model.customer_id),
        )

        # Set status
        from applications.ecommerce.modules.order.domain.order_status import OrderStatus

        order.status = OrderStatus(model.status)

        # Set dates
        order.created_at = model.created_at
        order.paid_at = model.paid_at
        order.cancelled_at = model.cancelled_at

        # Load items
        order.items.clear()  # Clear default empty list
        for item_model in model.items:
            item = OrderItem(
                product_id=ID(item_model.product_id),
                product_name=item_model.product_name,
                quantity=item_model.quantity,
                unit_price=item_model.unit_price,
            )
            # Note: Item ID will be newly generated, which is OK for this use case
            # In production, you might want to add a factory method to OrderItem
            # that accepts an optional ID parameter
            order.items.append(item)

        # Clear events (loaded from DB, no need to re-publish)
        order.clear_events()

        return order

    def _to_model(self, order: Order) -> OrderModel:
        """Convert Order to OrderModel."""
        return OrderModel(
            id=order.id.value,
            customer_id=order.customer_id.value,
            status=order.status.value,
            created_at=order.created_at,
            paid_at=order.paid_at,
            cancelled_at=order.cancelled_at,
        )

    async def find_by_customer_id(self, customer_id: ID) -> list[Order]:
        """Find orders by customer ID.

        Args:
            customer_id: Customer identifier

        Returns:
            List of orders for the customer

        Example:
            ```python
            orders = await order_repo.find_by_customer_id(customer_id)
            ```
        """
        from sqlalchemy.orm import selectinload

        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.customer_id == customer_id.value)
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def find_by_status(self, status: OrderStatus) -> list[Order]:
        """Find orders by status.

        Args:
            status: Order status

        Returns:
            List of orders with the given status

        Example:
            ```python
            pending_orders = await order_repo.find_by_status(OrderStatus.PENDING)
            ```
        """
        from sqlalchemy.orm import selectinload

        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.status == status.value)
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]
