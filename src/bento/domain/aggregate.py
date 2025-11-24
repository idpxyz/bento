"""Aggregate Root base class.

Aggregates are clusters of domain objects that can be treated as a single unit.
An aggregate root is the entry point to the aggregate.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from bento.core.ids import EntityId
from bento.domain.domain_event import DomainEvent
from bento.domain.entity import Entity


class AggregateRoot(Entity):
    """Base class for aggregate roots.

    An aggregate root is an entity that serves as the entry point to an aggregate.
    All operations on the aggregate must go through the aggregate root.

    Example:
        ```python
        class Order(AggregateRoot):
            def __init__(self, order_id: ID):
                super().__init__(order_id)
                self._items = []

            def add_item(self, item: OrderItem):
                self._items.append(item)
                self.add_event(ItemAdded(self.id, item.id))
        ```
    """

    def __init__(self, id):
        """Initialize aggregate root.

        Args:
            id: Entity identifier
        """
        super().__init__(id=id)
        self._events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event.

        Args:
            event: Domain event to add
        """
        self._events.append(event)

    def clear_events(self) -> None:
        """Clear all domain events."""
        self._events.clear()

    @property
    def events(self) -> list[DomainEvent]:
        """Get all domain events.

        Returns:
            List of domain events
        """
        return self._events.copy()

    def to_cache_dict(self) -> dict[str, Any]:
        """Convert aggregate root to cacheable dictionary.

        This method provides a default implementation for cache serialization.
        It automatically converts common types (ID, Decimal, datetime, Enum) to
        JSON-serializable formats.

        Override this method in subclasses if you need:
        - Custom serialization logic
        - To exclude certain fields from cache
        - To include computed properties

        Returns:
            Dictionary with JSON-serializable values

        Example:
            ```python
            class Product(AggregateRoot):
                def to_cache_dict(self) -> dict:
                    # Custom implementation - only cache essential fields
                    return {
                        "id": str(self.id),
                        "name": self.name,
                        "price": float(self.price),
                        # Exclude large fields like description
                    }
            ```
        """
        result: dict[str, Any] = {}

        for key, value in self.__dict__.items():
            # Skip private attributes and events
            if key.startswith("_"):
                continue

            # Convert special types to JSON-serializable formats
            result[key] = self._serialize_value(value)

        return result

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value to JSON-compatible format.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        # EntityId types (ID, OrderId, etc.)
        if isinstance(value, EntityId):
            return str(value)

        # Decimal to float
        if isinstance(value, Decimal):
            return float(value)

        # Datetime types
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        # Enum to value
        if isinstance(value, Enum):
            return value.value

        # List - recursively serialize
        if isinstance(value, list):
            return [
                item.to_cache_dict()
                if hasattr(item, "to_cache_dict")
                else self._serialize_value(item)
                for item in value
            ]

        # Dict - recursively serialize
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # Nested aggregate/entity with to_cache_dict
        if hasattr(value, "to_cache_dict"):
            return value.to_cache_dict()

        # Primitive types (str, int, float, bool, None)
        return value
