"""Order query service.

This module demonstrates CQRS query-side best practices:
- Separation of read and write models
- Query optimization
- Pagination and filtering
- Performance considerations
"""

import logging
from typing import Any
from uuid import UUID

from bento.core.errors import ApplicationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from applications.ecommerce.modules.order.errors import OrderErrors
from applications.ecommerce.modules.order.persistence.models.order_model import OrderModel
from bento.core.ids import ID
from bento.persistence.specification import SortDirection
from bento.persistence.specification.builder import FluentSpecificationBuilder

logger = logging.getLogger(__name__)


class OrderQueryService:
    """Service for querying orders (CQRS Read Model).

    This service demonstrates:
    - CQRS query-side patterns
    - Query optimization techniques
    - Separation from command handling
    - Performance best practices

    Best Practices:
    - Separate queries from commands
    - Optimize for read performance
    - Use database-level filtering and pagination
    - Return lightweight DTOs instead of domain objects
    - Avoid N+1 queries with eager loading
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize query service.

        Args:
            session: Database session for queries

        Best Practice:
        - Query services take session directly (no UoW needed)
        - Read-only operations don't need transaction management
        """
        self._session = session

    async def get_order_by_id(self, order_id: ID | UUID | str) -> dict[str, Any]:
        """Get order by ID.

        Args:
            order_id: Order identifier

        Returns:
            Order data as dictionary

        Raises:
            ApplicationError: If order not found

        Best Practices Demonstrated:
        - Eager loading to avoid N+1 queries
        - Return DTOs (dicts) instead of domain objects
        - Single database query for order + items
        """
        # Convert to UUID if needed
        if isinstance(order_id, ID):
            order_id_value = order_id.value
        elif isinstance(order_id, str):
            order_id_value = UUID(order_id)
        else:
            order_id_value = order_id

        # Use selectinload for eager loading to avoid N+1 queries
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id_value)
            .options(selectinload(OrderModel.items))  # Eager load items
        )

        result = await self._session.execute(stmt)
        order_po = result.scalar_one_or_none()

        if not order_po:
            logger.warning(f"Order not found: {order_id_value}")
            raise ApplicationError(
                error_code=OrderErrors.ORDER_NOT_FOUND,
                details={"order_id": str(order_id_value)},
            )

        logger.debug(f"Found order: {order_id_value}")
        return self._order_to_dict(order_po)

    async def list_orders(
        self,
        *,
        customer_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List orders with filtering and pagination.

        Args:
            customer_id: Filter by customer ID (optional)
            status: Filter by order status (optional)
            limit: Maximum number of results (default: 20, max: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            Dictionary with:
            - items: List of order data
            - total: Total count of matching orders
            - limit: Applied limit
            - offset: Applied offset

        Best Practices Demonstrated:
        - Database-level filtering
        - Efficient pagination
        - Count query optimization
        - Limit validation to prevent excessive queries
        """
        # Validate and cap limit
        limit = min(max(1, limit), 100)  # Between 1 and 100
        offset = max(0, offset)

        logger.debug(
            f"Listing orders: customer_id={customer_id}, status={status}, "
            f"limit={limit}, offset={offset}"
        )

        # Build query with filters
        stmt = select(OrderModel).options(selectinload(OrderModel.items))

        if customer_id:
            stmt = stmt.where(OrderModel.customer_id == customer_id)
        if status:
            stmt = stmt.where(OrderModel.status == status)

        # Apply sorting (newest first)
        stmt = stmt.order_by(OrderModel.created_at.desc())

        # Get total count (for pagination metadata)
        count_stmt = select(func.count()).select_from(OrderModel)
        if customer_id:
            count_stmt = count_stmt.where(OrderModel.customer_id == customer_id)
        if status:
            count_stmt = count_stmt.where(OrderModel.status == status)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        # Execute query
        result = await self._session.execute(stmt)
        orders = result.scalars().all()

        logger.info(
            f"Found {len(orders)} orders (total: {total}, limit: {limit}, offset: {offset})"
        )

        return {
            "items": [self._order_to_dict(order) for order in orders],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(orders) < total,
        }

    async def search_orders(
        self,
        *,
        min_amount: float | None = None,
        max_amount: float | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search orders with advanced filters.

        Args:
            min_amount: Minimum total amount
            max_amount: Maximum total amount
            from_date: Start date (ISO format)
            to_date: End date (ISO format)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Dictionary with search results and pagination metadata

        Best Practices Demonstrated:
        - Complex filtering at database level
        - Date range queries
        - Numeric range queries
        - Efficient query building
        """
        # Validate and cap limit
        limit = min(max(1, limit), 100)
        offset = max(0, offset)

        logger.debug(
            f"Searching orders: min_amount={min_amount}, max_amount={max_amount}, "
            f"from_date={from_date}, to_date={to_date}"
        )

        # Build query with filters
        stmt = select(OrderModel).options(selectinload(OrderModel.items))

        # Note: Amount filtering is done in-memory after query
        # because total_amount is computed from items

        # Date range filter
        if from_date:
            stmt = stmt.where(OrderModel.created_at >= from_date)
        if to_date:
            stmt = stmt.where(OrderModel.created_at <= to_date)

        # Apply sorting
        stmt = stmt.order_by(OrderModel.created_at.desc())

        # Get total count (without amount filter)
        count_stmt = select(func.count()).select_from(OrderModel)
        if from_date:
            count_stmt = count_stmt.where(OrderModel.created_at >= from_date)
        if to_date:
            count_stmt = count_stmt.where(OrderModel.created_at <= to_date)

        # Execute query (no pagination yet, need to filter by amount first)
        result = await self._session.execute(stmt)
        all_orders = result.scalars().all()

        # Filter by amount in memory
        filtered_orders = []
        for order in all_orders:
            total = order.total_amount
            if min_amount is not None and total < min_amount:
                continue
            if max_amount is not None and total > max_amount:
                continue
            filtered_orders.append(order)

        # Apply pagination to filtered results
        total = len(filtered_orders)
        paginated_orders = filtered_orders[offset : offset + limit]

        logger.info(f"Search found {len(paginated_orders)} orders (total: {total})")

        return {
            "items": [self._order_to_dict(order) for order in paginated_orders],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(paginated_orders) < total,
        }

    async def get_order_statistics(self, customer_id: str | None = None) -> dict[str, Any]:
        """Get order statistics.

        Args:
            customer_id: Filter by customer ID (optional)

        Returns:
            Statistics including:
            - total_orders: Total number of orders
            - total_revenue: Sum of all paid orders
            - average_order_value: Average order amount
            - status_breakdown: Count by status

        Best Practices Demonstrated:
        - Aggregation queries
        - Database-level calculations
        - Efficient statistics gathering
        """
        logger.debug(f"Getting order statistics for customer: {customer_id}")

        # Query all orders with items (need to calculate amounts)
        stmt = select(OrderModel).options(selectinload(OrderModel.items))
        if customer_id:
            stmt = stmt.where(OrderModel.customer_id == customer_id)

        result = await self._session.execute(stmt)
        orders = result.scalars().all()

        # Calculate statistics in memory
        total_orders = len(orders)
        total_revenue = sum(order.total_amount for order in orders if order.status == "paid")
        average_order_value = (
            sum(order.total_amount for order in orders) / total_orders if total_orders > 0 else 0
        )

        # Status breakdown
        status_stmt = select(OrderModel.status, func.count(OrderModel.id).label("count")).group_by(
            OrderModel.status
        )
        if customer_id:
            status_stmt = status_stmt.where(OrderModel.customer_id == customer_id)

        status_result = await self._session.execute(status_stmt)
        status_breakdown = {row.status: row.count for row in status_result}

        statistics = {
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "average_order_value": float(average_order_value),
            "status_breakdown": status_breakdown,
        }

        logger.info(f"Statistics: {statistics}")
        return statistics

    async def list_orders_with_specification(
        self,
        *,
        customer_id: str | None = None,
        status: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List orders using Specification pattern.

        This method demonstrates how to use the Specification pattern
        for building complex queries in a clean, reusable way.

        Args:
            customer_id: Filter by customer ID
            status: Filter by order status
            min_amount: Minimum total amount
            max_amount: Maximum total amount
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Dictionary with filtered and paginated results

        Best Practices Demonstrated:
        - Specification pattern for query building
        - Fluent API for readable query construction
        - Reusable filter logic
        - Type-safe query building
        """
        logger.debug(
            f"List orders with spec: customer={customer_id}, status={status}, "
            f"amount_range=({min_amount},{max_amount}), page={page}"
        )

        # Build specification using FluentSpecificationBuilder
        builder = FluentSpecificationBuilder(OrderModel)

        if customer_id:
            builder = builder.equals("customer_id", customer_id)
        if status:
            builder = builder.equals("status", status)

        # Amount range filtering (emit separate constraints)
        if min_amount is not None:
            builder = builder.greater_than_or_equal("total_amount", min_amount)
        if max_amount is not None:
            builder = builder.less_than_or_equal("total_amount", max_amount)

        # Sorting and pagination
        spec = (
            builder.order_by("created_at", descending=True)
            .paginate(page=page, size=min(page_size, 100))
            .build()
        )

        # Apply specification to SQLAlchemy query
        # NOTE: In a full implementation, you would have a helper method
        # to convert Specification to SQLAlchemy filters
        stmt = select(OrderModel).options(selectinload(OrderModel.items))

        # Apply filters from specification (skip total_amount - computed property)
        for filter in spec.filters:
            if filter.field == "customer_id":
                stmt = stmt.where(OrderModel.customer_id == filter.value)
            elif filter.field == "status":
                stmt = stmt.where(OrderModel.status == filter.value)
            # Note: total_amount filtering will be done in-memory after query

        # Apply sorting
        for sort in spec.sorts:
            if sort.field == "created_at":
                stmt = stmt.order_by(
                    OrderModel.created_at.desc()
                    if sort.direction == SortDirection.DESC
                    else OrderModel.created_at.asc()
                )

        # Note: Pagination is applied AFTER in-memory filtering

        # Execute query
        result = await self._session.execute(stmt)
        all_orders = result.scalars().all()

        # Apply in-memory filters for total_amount
        filtered_orders = []
        for order in all_orders:
            # Check amount filters from specification
            passes_filter = True
            for filter in spec.filters:
                if filter.field == "total_amount":
                    from bento.persistence.specification import FilterOperator

                    total = order.total_amount
                    if filter.operator == FilterOperator.BETWEEN:
                        if not (filter.value["start"] <= total <= filter.value["end"]):
                            passes_filter = False
                            break
                    elif filter.operator == FilterOperator.GREATER_EQUAL:
                        if not (total >= filter.value):
                            passes_filter = False
                            break
                    elif filter.operator == FilterOperator.LESS_EQUAL:
                        if not (total <= filter.value):
                            passes_filter = False
                            break

            if passes_filter:
                filtered_orders.append(order)

        # Apply pagination to filtered results
        total = len(filtered_orders)
        if spec.page:
            offset = (spec.page.page - 1) * spec.page.size
            paginated_orders = filtered_orders[offset : offset + spec.page.size]
        else:
            paginated_orders = filtered_orders

        logger.info(f"Found {len(paginated_orders)} orders using Specification (total: {total})")

        return {
            "items": [self._order_to_dict(order) for order in paginated_orders],
            "total": total,
            "page": spec.page.page if spec.page else 1,
            "page_size": spec.page.size if spec.page else len(paginated_orders),
            "total_pages": (total + spec.page.size - 1) // spec.page.size if spec.page else 1,
        }

    def _order_to_dict(self, order_po: OrderModel) -> dict[str, Any]:
        """Convert OrderModel to dictionary (DTO).

        Args:
            order_po: Order persistence object

        Returns:
            Order data as dictionary

        Best Practice:
        - Create lightweight DTOs for API responses
        - Include only necessary data
        - Format dates consistently
        """
        return {
            "id": str(order_po.id),
            "customer_id": order_po.customer_id,
            "status": order_po.status,
            "items": [
                {
                    "id": str(item.id),
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.subtotal),
                }
                for item in order_po.items
            ],
            "items_count": len(order_po.items),
            "total_amount": float(order_po.total_amount),
            "created_at": order_po.created_at.isoformat() if order_po.created_at else None,
            "paid_at": order_po.paid_at.isoformat() if order_po.paid_at else None,
            "cancelled_at": order_po.cancelled_at.isoformat() if order_po.cancelled_at else None,
        }
