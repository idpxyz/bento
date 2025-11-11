"""Order read service using CQRS read models.

This service queries the optimized read models instead of the write models,
providing better performance for complex queries.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from applications.ecommerce.modules.order.persistence.models.order_read_model import (
    OrderReadModel,
)
from bento.core.errors import ApplicationError
from bento.core.ids import ID

logger = logging.getLogger(__name__)


class OrderReadService:
    """Query service using CQRS read models.

    Advantages over write model queries:
    - Pre-calculated fields (total_amount) allow database-level filtering
    - Denormalized data eliminates joins
    - Optimized indexes for common queries
    - No N+1 query problems

    Trade-offs:
    - Eventual consistency (read model slightly behind write model)
    - Additional storage for read models
    - Need to maintain sync logic
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize read service.

        Args:
            session: Database session for read-only queries
        """
        self._session = session

    async def get_order_by_id(self, order_id: ID | str) -> dict[str, Any]:
        """Get order from read model.

        Args:
            order_id: Order identifier

        Returns:
            Order data as dictionary

        Raises:
            ApplicationError: If order not found
        """
        order_id_str = order_id.value if isinstance(order_id, ID) else order_id

        stmt = select(OrderReadModel).where(OrderReadModel.id == order_id_str)
        result = await self._session.execute(stmt)
        read_model = result.scalar_one_or_none()

        if not read_model:
            raise ApplicationError(
                error_code="ORDER_NOT_FOUND",
                details={"order_id": order_id_str},
            )

        return self._to_dict(read_model)

    async def search_orders(
        self,
        *,
        customer_id: str | None = None,
        status: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search orders with filters - using read model for efficiency.

        Key benefit: total_amount filtering happens at database level!

        Args:
            customer_id: Filter by customer
            status: Filter by status
            min_amount: Minimum total amount
            max_amount: Maximum total amount
            limit: Page size
            offset: Page offset

        Returns:
            Search results with pagination
        """
        limit = min(max(1, limit), 100)
        offset = max(0, offset)

        # Build query with database-level filters
        stmt = select(OrderReadModel)

        if customer_id:
            stmt = stmt.where(OrderReadModel.customer_id == customer_id)
        if status:
            stmt = stmt.where(OrderReadModel.status == status)

        # ✅ Database-level amount filtering (this was the problem before!)
        if min_amount is not None:
            stmt = stmt.where(OrderReadModel.total_amount >= min_amount)
        if max_amount is not None:
            stmt = stmt.where(OrderReadModel.total_amount <= max_amount)

        # Sorting
        stmt = stmt.order_by(OrderReadModel.created_at.desc())

        # Get total count
        count_stmt = select(func.count()).select_from(OrderReadModel)
        if customer_id:
            count_stmt = count_stmt.where(OrderReadModel.customer_id == customer_id)
        if status:
            count_stmt = count_stmt.where(OrderReadModel.status == status)
        if min_amount is not None:
            count_stmt = count_stmt.where(OrderReadModel.total_amount >= min_amount)
        if max_amount is not None:
            count_stmt = count_stmt.where(OrderReadModel.total_amount <= max_amount)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        # Execute
        result = await self._session.execute(stmt)
        orders = result.scalars().all()

        logger.info(f"Read model search found {len(orders)} orders (total: {total})")

        return {
            "items": [self._to_dict(order) for order in orders],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(orders) < total,
        }

    async def get_statistics(self, customer_id: str | None = None) -> dict[str, Any]:
        """Get order statistics from read models.

        Much faster than write model because:
        - total_amount is pre-calculated
        - No need to join with items table

        Args:
            customer_id: Filter by customer (optional)

        Returns:
            Order statistics
        """
        # Aggregate queries on read model
        from sqlalchemy import case

        stats_stmt = select(
            func.count(OrderReadModel.id).label("total_orders"),
            func.sum(
                case((OrderReadModel.status == "paid", OrderReadModel.total_amount), else_=0)
            ).label("total_revenue"),
            func.avg(OrderReadModel.total_amount).label("average_order_value"),
        )

        if customer_id:
            stats_stmt = stats_stmt.where(OrderReadModel.customer_id == customer_id)

        stats_result = await self._session.execute(stats_stmt)
        stats_row = stats_result.one()

        # Status breakdown
        status_stmt = select(
            OrderReadModel.status, func.count(OrderReadModel.id).label("count")
        ).group_by(OrderReadModel.status)

        if customer_id:
            status_stmt = status_stmt.where(OrderReadModel.customer_id == customer_id)

        status_result = await self._session.execute(status_stmt)
        status_breakdown = {row.status: row.count for row in status_result}

        return {
            "total_orders": stats_row.total_orders or 0,
            "total_revenue": float(stats_row.total_revenue or 0),
            "average_order_value": float(stats_row.average_order_value or 0),
            "status_breakdown": status_breakdown,
        }

    def _to_dict(self, read_model: OrderReadModel) -> dict[str, Any]:
        """Convert read model to dictionary."""
        return {
            "id": read_model.id,
            "customer_id": read_model.customer_id,
            "status": read_model.status,
            "total_amount": float(read_model.total_amount),
            "items_count": read_model.items_count,
            "created_at": read_model.created_at.isoformat() if read_model.created_at else None,
            "updated_at": read_model.updated_at.isoformat() if read_model.updated_at else None,
            "paid_at": read_model.paid_at.isoformat() if read_model.paid_at else None,
            "cancelled_at": (
                read_model.cancelled_at.isoformat() if read_model.cancelled_at else None
            ),
        }
