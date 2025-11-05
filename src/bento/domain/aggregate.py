"""Aggregate Root base class.

Aggregates are clusters of domain objects that can be treated as a single unit.
An aggregate root is the entry point to the aggregate.
"""

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
