"""Repository ports for Ordering context.

Repository ports define the contract for data persistence.
Following Hexagonal Architecture principles.

Note: OrderItem does not have a separate repository as it's part of
the Order aggregate. Access OrderItems through IOrderRepository.
"""

from contexts.ordering.domain.ports.repositories.i_order_repository import (
    IOrderRepository,
)

__all__ = [
    "IOrderRepository",
]
