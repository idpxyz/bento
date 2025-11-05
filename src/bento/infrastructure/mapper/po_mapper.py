"""Persistence Object Mapper implementation.

This module provides the implementation for mapping between Domain objects (Aggregate Roots)
and Persistence Objects (POs) used by SQLAlchemy.

Key Components:
- POMapper: Base implementation of BidirectionalCollectionMapper for AR �?PO
"""

from typing import Any

from bento.application.ports.mapper import BidirectionalCollectionMapper


class POMapper[D, P](BidirectionalCollectionMapper[D, P]):
    """Persistence Object Mapper for AR �?PO transformation.

    This mapper provides bidirectional mapping between Domain objects
    (Aggregate Roots) and Persistence Objects (SQLAlchemy models).

    Features:
    - Auto-mapping based on field names
    - Custom mapping override support
    - Batch operations optimization
    - Type-safe generic implementation

    Example:
        ```python
        # Auto-mapping (simple case)
        class UserPOMapper(POMapper[User, UserPO]):
            def __init__(self):
                super().__init__(
                    domain_type=User,
                    po_type=UserPO,
                    auto_map=True
                )

        # Custom mapping
        class OrderPOMapper(POMapper[Order, OrderPO]):
            def __init__(self):
                super().__init__(
                    domain_type=Order,
                    po_type=OrderPO,
                    auto_map=False
                )

            def _map_to_po(self, order: Order) -> OrderPO:
                return OrderPO(
                    id=order.id.value,
                    customer_id=order.customer.id.value,
                    total=order.calculate_total(),
                )

            def _map_to_domain(self, po: OrderPO) -> Order:
                return Order(
                    id=OrderId(po.id),
                    customer=Customer(id=CustomerId(po.customer_id)),
                    # ... other fields
                )
        ```
    """

    def __init__(
        self,
        domain_type: type[D],
        po_type: type[P],
        auto_map: bool = True,
        field_mapping: dict[str, str] | None = None,
    ) -> None:
        """Initialize POMapper.

        Args:
            domain_type: Domain object type (Aggregate Root)
            po_type: Persistence object type (SQLAlchemy model)
            auto_map: Whether to enable auto-mapping (default: True)
            field_mapping: Custom field name mappings (domain_field -> po_field)
        """
        self._domain_type = domain_type
        self._po_type = po_type
        self._auto_map = auto_map
        self._field_mapping = field_mapping or {}

    # ==================== BidirectionalMapper Implementation ====================

    def map(self, domain: D) -> P:
        """Map domain object to persistence object (AR �?PO).

        Args:
            domain: Domain object to map

        Returns:
            Persistence object

        Example:
            ```python
            user = User(id="user-001", name="John")
            user_po = mapper.map(user)  # AR �?PO
            ```
        """
        return self.to_po(domain)

    def map_reverse(self, po: P) -> D:
        """Map persistence object back to domain object (PO �?AR).

        Args:
            po: Persistence object to map back

        Returns:
            Domain object

        Example:
            ```python
            user_po = await session.get(UserPO, "user-001")
            user = mapper.map_reverse(user_po)  # PO �?AR
            ```
        """
        return self.to_domain(po)

    # ==================== CollectionMapper Implementation ====================

    def map_list(self, domains: list[D]) -> list[P]:
        """Map list of domain objects to persistence objects (batch AR �?PO).

        Args:
            domains: List of domain objects

        Returns:
            List of persistence objects

        Note:
            This implementation uses list comprehension for efficiency.
            Subclasses can override for further optimization.
        """
        return self.to_pos(domains)

    def map_reverse_list(self, pos: list[P]) -> list[D]:
        """Map list of persistence objects back to domain objects (batch PO �?AR).

        Args:
            pos: List of persistence objects

        Returns:
            List of domain objects
        """
        return self.to_domains(pos)

    # ==================== Semantic Methods ====================

    def to_po(self, domain: D) -> P:
        """Convert domain object to persistence object (AR �?PO).

        Semantic alias for map() with clearer intent.

        Args:
            domain: Domain object to convert

        Returns:
            Persistence object
        """
        if self._auto_map:
            return self._auto_map_to_po(domain)
        else:
            return self._map_to_po(domain)

    def to_domain(self, po: P) -> D:
        """Convert persistence object to domain object (PO �?AR).

        Semantic alias for map_reverse() with clearer intent.

        Args:
            po: Persistence object to convert

        Returns:
            Domain object
        """
        if self._auto_map:
            return self._auto_map_to_domain(po)
        else:
            return self._map_to_domain(po)

    def to_pos(self, domains: list[D]) -> list[P]:
        """Batch convert domain objects to persistence objects.

        Args:
            domains: List of domain objects

        Returns:
            List of persistence objects
        """
        if not domains:
            return []
        return [self.to_po(d) for d in domains]

    def to_domains(self, pos: list[P]) -> list[D]:
        """Batch convert persistence objects to domain objects.

        Args:
            pos: List of persistence objects

        Returns:
            List of domain objects
        """
        if not pos:
            return []
        return [self.to_domain(p) for p in pos]

    # ==================== Auto-Mapping Implementation ====================

    def _auto_map_to_po(self, domain: D) -> P:
        """Auto-map domain object to persistence object.

        Uses field name matching with optional field mapping overrides.

        Args:
            domain: Domain object to map

        Returns:
            Persistence object

        Note:
            This is a simplified auto-mapping implementation.
            For complex cases, override _map_to_po() instead.
        """
        po_dict: dict[str, Any] = {}

        # Get common fields
        domain_attrs = self._get_domain_attributes(domain)
        po_fields = self._get_po_fields()

        for domain_field in domain_attrs:
            # Check if there's a custom mapping
            po_field = self._field_mapping.get(domain_field, domain_field)

            # Only map if PO has this field
            if po_field in po_fields:
                value = getattr(domain, domain_field, None)
                # Handle ValueObjects (extract .value if exists)
                if value is not None and hasattr(value, "value"):
                    value = value.value
                po_dict[po_field] = value

        return self._po_type(**po_dict)

    def _auto_map_to_domain(self, po: P) -> D:
        """Auto-map persistence object to domain object.

        Uses field name matching with optional field mapping overrides.

        Args:
            po: Persistence object to map

        Returns:
            Domain object

        Note:
            This is a simplified auto-mapping implementation.
            For complex cases, override _map_to_domain() instead.
        """
        domain_dict: dict[str, Any] = {}

        # Reverse field mapping
        reverse_mapping = {v: k for k, v in self._field_mapping.items()}

        # Get fields
        po_attrs = self._get_po_attributes(po)
        domain_fields = self._get_domain_fields()

        for po_field in po_attrs:
            # Check if there's a custom mapping
            domain_field = reverse_mapping.get(po_field, po_field)

            # Only map if Domain has this field
            if domain_field in domain_fields:
                value = getattr(po, po_field, None)
                domain_dict[domain_field] = value

        return self._domain_type(**domain_dict)

    # ==================== Custom Mapping Override Points ====================

    def _map_to_po(self, domain: D) -> P:
        """Custom mapping from domain to persistence object.

        Override this method for custom mapping logic.

        Args:
            domain: Domain object to map

        Returns:
            Persistence object

        Raises:
            NotImplementedError: If auto_map=False but not overridden
        """
        raise NotImplementedError(
            f"Custom mapping not implemented for "
            f"{self._domain_type.__name__} -> {self._po_type.__name__}. "
            f"Either set auto_map=True or override _map_to_po()."
        )

    def _map_to_domain(self, po: P) -> D:
        """Custom mapping from persistence object to domain.

        Override this method for custom mapping logic.

        Args:
            po: Persistence object to map

        Returns:
            Domain object

        Raises:
            NotImplementedError: If auto_map=False but not overridden
        """
        raise NotImplementedError(
            f"Custom mapping not implemented for "
            f"{self._po_type.__name__} -> {self._domain_type.__name__}. "
            f"Either set auto_map=True or override _map_to_domain()."
        )

    # ==================== Helper Methods ====================

    def _get_domain_attributes(self, domain: D) -> list[str]:
        """Get list of domain object attributes.

        Args:
            domain: Domain object instance

        Returns:
            List of attribute names
        """
        # Get instance attributes (excluding private ones)
        return [
            attr
            for attr in dir(domain)
            if not attr.startswith("_") and not callable(getattr(domain, attr))
        ]

    def _get_po_attributes(self, po: P) -> list[str]:
        """Get list of persistence object attributes.

        Args:
            po: Persistence object instance

        Returns:
            List of attribute names
        """
        # For SQLAlchemy models, get column names
        table = getattr(po.__class__, "__table__", None)
        if table is not None:
            return [col.name for col in table.columns]

        # Fallback to dir()
        return [
            attr for attr in dir(po) if not attr.startswith("_") and not callable(getattr(po, attr))
        ]

    def _get_domain_fields(self) -> list[str]:
        """Get list of domain type fields.

        Returns:
            List of field names
        """
        # Try to get from type hints
        if hasattr(self._domain_type, "__annotations__"):
            return list(self._domain_type.__annotations__.keys())

        # Fallback
        return []

    def _get_po_fields(self) -> list[str]:
        """Get list of persistence object fields.

        Returns:
            List of field names
        """
        # For SQLAlchemy models
        table = getattr(self._po_type, "__table__", None)
        if table is not None:
            return [col.name for col in table.columns]

        # Fallback to annotations
        if hasattr(self._po_type, "__annotations__"):
            return list(self._po_type.__annotations__.keys())

        return []
