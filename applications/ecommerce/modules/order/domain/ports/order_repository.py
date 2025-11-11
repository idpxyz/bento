"""Order repository port (interface).

Defines the contract for Order repository implementations.
Domain layer defines the interface; infrastructure layer implements it.
"""

from typing import Protocol

from applications.ecommerce.modules.order.domain.order import Order
from bento.core.ids import ID
from bento.persistence.specification import CompositeSpecification, Page, PageParams


class IOrderRepository(Protocol):
    """Order repository interface (port).

    This is the contract that infrastructure adapters must implement.
    The domain layer depends on this interface, not the concrete implementation.
    """

    async def get(self, id: ID) -> Order | None:
        """Get order by ID.

        Args:
            id: Order identifier

        Returns:
            Order if found, None otherwise
        """
        ...

    async def save(self, order: Order) -> None:
        """Save order (create or update).

        Args:
            order: Order aggregate to save
        """
        ...

    async def delete(self, order: Order) -> None:
        """Delete order (soft delete).

        Args:
            order: Order aggregate to delete
        """
        ...

    async def list(self, specification: CompositeSpecification | None = None) -> list[Order]:
        """List orders matching specification.

        Args:
            specification: Optional filter criteria

        Returns:
            List of matching orders
        """
        ...

    async def find_one(self, specification: CompositeSpecification) -> Order | None:
        """Find single order matching specification.

        Args:
            specification: Filter criteria

        Returns:
            Order if found, None otherwise
        """
        ...

    async def find_page(
        self,
        specification: CompositeSpecification,
        page_params: PageParams,
    ) -> Page[Order]:
        """Find page of orders matching specification.

        Args:
            specification: Filter criteria
            page_params: Pagination parameters

        Returns:
            Page of orders
        """
        ...

    async def count(self, specification: CompositeSpecification | None = None) -> int:
        """Count orders matching specification.

        Args:
            specification: Optional filter criteria

        Returns:
            Count of matching orders
        """
        ...

    async def exists(self, specification: CompositeSpecification) -> bool:
        """Check if any order matches specification.

        Args:
            specification: Filter criteria

        Returns:
            True if at least one match exists
        """
        ...

    # ==================== Custom Queries ====================

    async def find_unpaid(self) -> list[Order]:
        """Find all unpaid orders.

        Returns:
            List of unpaid orders
        """
        ...

    async def find_by_customer(self, customer_id: ID) -> list[Order]:
        """Find all orders for a specific customer.

        Args:
            customer_id: Customer identifier

        Returns:
            List of customer orders
        """
        ...

    async def find_by_status(self, status: str) -> list[Order]:
        """Find orders by status.

        Args:
            status: Order status

        Returns:
            List of orders with given status
        """
        ...

    async def find_recent(self, limit: int) -> list[Order]:
        """Find most recent orders.

        Args:
            limit: Maximum number of orders

        Returns:
            List of recent orders
        """
        ...

    async def count_by_status(self, status: str) -> int:
        """Count orders by status."""
        ...

    async def has_customer_orders(self, customer_id: ID) -> bool:
        """Check if customer has any orders."""
        ...
