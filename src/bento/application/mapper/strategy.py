"""Base strategy for all mappers.

This module defines the abstract base class for mapper implementations,
ensuring all mappers follow the Mapper protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable


class MapperStrategy[Domain, PO](ABC):
    """Abstract base class for all mapper strategies.

    All concrete mapper implementations (BaseMapper, AutoMapper)
    must extend this class and implement the Mapper protocol.

    Type Parameters:
        Domain: Domain object type (AggregateRoot or Entity)
        PO: Persistence Object type (SQLAlchemy model)

    Note:
        This is an ABC (not a Protocol) to enforce common initialization
        and provide utility methods for subclasses.

    Usage:
        Prefer AutoMapper (90% use cases) or BaseMapper (10% use cases).
    """

    def __init__(self, domain_type: type[Domain], po_type: type[PO]) -> None:
        """Initialize mapper with type information.

        Args:
            domain_type: Domain object class
            po_type: Persistence object class
        """
        self._domain_type = domain_type
        self._po_type = po_type

    @property
    def domain_type(self) -> type[Domain]:
        """Get domain object type."""
        return self._domain_type

    @property
    def po_type(self) -> type[PO]:
        """Get persistence object type."""
        return self._po_type

    # ---- Core abstract APIs ----
    @abstractmethod
    def map(self, domain: Domain) -> PO:
        """Map domain object to persistence object.

        Args:
            domain: Domain object (AggregateRoot/Entity)

        Returns:
            Persistence object (SQLAlchemy model)

        Note:
            Implementations must handle:
            - Type conversion (EntityId → str, Enum → value)
            - Child entity mapping (if applicable)
            - NOT audit fields (handled by Interceptors)
        """
        ...

    @abstractmethod
    def map_reverse(self, po: PO) -> Domain:
        """Map persistence object back to domain object.

        Args:
            po: Persistence object (SQLAlchemy model)

        Returns:
            Domain object (AggregateRoot/Entity)

        Note:
            Implementations must handle:
            - Type reconstruction (str → EntityId, value → Enum)
            - Child entity reconstruction
            - Clearing domain events (loaded entities shouldn't re-publish)
        """
        ...

    # ---- Batch helpers (wider input types) ----
    def map_list(self, domains: Iterable[Domain]) -> list[PO]:
        """Map iterable of domain objects to persistence objects.

        Default implementation uses map() for each item.
        Override if you need batch optimization.

        Args:
            domains: Iterable of domain objects

        Returns:
            List of persistence objects
        """
        return [self.map(domain) for domain in domains]

    def map_reverse_list(self, pos: Iterable[PO]) -> list[Domain]:
        """Map iterable of persistence objects to domain objects.

        Default implementation uses map_reverse() for each item.
        Override if you need batch optimization.

        Args:
            pos: Iterable of persistence objects

        Returns:
            List of domain objects
        """
        return [self.map_reverse(po) for po in pos]

    # ---- Optional observability hooks ----
    def on_batch_mapped(self, src_count: int, dst_count: int) -> None:  # pragma: no cover
        """Hook called after batch mapping for metrics/logging.

        Override if you need to emit metrics or logs.

        Args:
            src_count: Number of source domain objects
            dst_count: Number of destination PO objects
        """
        return None

    def on_batch_reverse_mapped(self, src_count: int, dst_count: int) -> None:  # pragma: no cover
        """Hook called after batch reverse mapping for metrics/logging.

        Override if you need to emit metrics or logs.

        Args:
            src_count: Number of source PO objects
            dst_count: Number of destination domain objects
        """
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        dn = getattr(self._domain_type, "__name__", repr(self._domain_type))
        pn = getattr(self._po_type, "__name__", repr(self._po_type))
        return f"{self.__class__.__name__}({dn} ↔ {pn})"
