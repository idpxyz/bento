"""Order repository port (interface).

Defines the contract for Order repository implementations.
Domain layer defines the interface; infrastructure layer implements it.

Following Hexagonal Architecture:
- This interface is in domain/ports/repositories (Port)
- Implementation is in infrastructure/repositories (Adapter)
- Application layer depends on this interface, not implementation
"""

from __future__ import annotations

from typing import Protocol

from bento.core.ids import ID
from bento.domain.ports.repository import Repository

from contexts.ordering.domain.order import Order


class IOrderRepository(Repository[Order, ID], Protocol):
    """Order repository interface (Secondary Port).

    Inherits from Bento's Repository[Order, ID] protocol to get standard methods:
    - get(id: ID) -> Order | None
    - save(entity: Order) -> Order
    - delete(entity: Order) -> None
    - find_all() -> list[Order]
    - exists(id: ID) -> bool
    - count() -> int

    This interface extends with Order-specific queries below.

    Following Dependency Inversion Principle:
    - Domain layer defines the interface (this file)
    - Infrastructure layer implements it (infrastructure/repositories/)
    - Application layer depends on interface (not implementation)
    """

    # Standard methods are inherited from Repository[Order, ID]:
    # - async def get(id: ID) -> Order | None
    # - async def save(entity: Order) -> Order
    # - async def delete(entity: Order) -> None
    # - async def find_all() -> list[Order]
    # - async def exists(id: ID) -> bool
    # - async def count() -> int

    # Domain-specific query methods:
    async def find_by_customer(self, customer_id: str) -> list[Order]:
        """Find orders by customer ID.

        Args:
            customer_id: Customer identifier

        Returns:
            List of orders for the customer
        """
        ...
