"""Mapper protocol for Domain-PO transformation.

This module defines the core mapper protocol for Bento's DDD framework.
Follows the Dependency Inversion Principle.

Key Protocol:
- Mapper: Domain ↔ PO bidirectional mapping with semantic parameter names
"""

from typing import Protocol, TypeVar

# Type variables for Domain-PO mapping
Domain = TypeVar("Domain")  # Domain object (AggregateRoot/Entity)
PO = TypeVar("PO")  # Persistence Object (SQLAlchemy model)


class Mapper(Protocol[Domain, PO]):
    """Protocol for Domain ↔ PO mapping (Bento's core mapper).

    The primary mapper protocol for DDD applications, providing bidirectional
    mapping between Domain objects and Persistence Objects with semantic
    parameter names (domain/po) for clarity.

    Key Features:
    - Semantic parameter names: domain/po instead of source/target
    - Bidirectional: Domain → PO and PO → Domain
    - Batch operations: list[Domain] ↔ list[PO]
    - Seamless integration with RepositoryAdapter

    Example:
        ```python
        from bento.application.mapper import MapperStrategy

        class OrderMapper(MapperStrategy[Order, OrderModel]):
            def map(self, domain: Order) -> OrderModel:
                return OrderModel(
                    id=domain.id.value,
                    customer_id=domain.customer_id.value,
                    total=domain.total,
                )

            def map_reverse(self, po: OrderModel) -> Order:
                return Order(
                    order_id=ID(po.id),
                    customer_id=ID(po.customer_id),
                )

            # map_list() and map_reverse_list() inherited from MapperStrategy!
        ```

    Note:
        Use MapperStrategy as base class to automatically get map_list/map_reverse_list
        implementations. Or implement all four methods manually.
    """

    def map(self, domain: Domain) -> PO:
        """Map domain object to persistence object.

        Args:
            domain: Domain object (AggregateRoot/Entity)

        Returns:
            Persistence object (SQLAlchemy model)
        """
        ...

    def map_reverse(self, po: PO) -> Domain:
        """Map persistence object back to domain object.

        Args:
            po: Persistence object (SQLAlchemy model)

        Returns:
            Domain object (AggregateRoot/Entity)
        """
        ...

    def map_list(self, domains: list[Domain]) -> list[PO]:
        """Map list of domain objects to persistence objects.

        Args:
            domains: List of domain objects

        Returns:
            List of persistence objects

        Note:
            Default implementation: [self.map(d) for d in domains]
            Override for optimized batch processing if needed.
        """
        ...

    def map_reverse_list(self, pos: list[PO]) -> list[Domain]:
        """Map list of persistence objects to domain objects.

        Args:
            pos: List of persistence objects

        Returns:
            List of domain objects

        Note:
            Default implementation: [self.map_reverse(p) for p in pos]
            Override for optimized batch processing if needed.
        """
        ...


__all__ = [
    "Mapper",
    "Domain",
    "PO",
]
