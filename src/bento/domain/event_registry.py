"""Event Registry for event serialization and deserialization.

This module provides a centralized registry for all domain events,
enabling proper deserialization from the Outbox table.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from bento.domain.domain_event import DomainEvent

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="DomainEvent")

# Global event registry: event_type_name -> event_class
_EVENT_REGISTRY: dict[str, type[DomainEvent]] = {}


def register_event(event_class: type[T]) -> type[T]:
    """Decorator to register a domain event class.

    This allows the Projector to deserialize events from the Outbox
    table back to their specific event types.

    Args:
        event_class: The domain event class to register

    Returns:
        The same event class (allows using as decorator)

    Example:
        ```python
        from bento.domain.domain_event import DomainEvent
        from bento.domain.event_registry import register_event

        @register_event
        @dataclass(frozen=True)
        class OrderCreatedEvent(DomainEvent):
            order_id: str
            customer_id: str
            total_amount: float
        ```
    """
    event_name = event_class.__name__
    if event_name in _EVENT_REGISTRY:
        logger.warning(
            "Event %s is already registered, overwriting with %s",
            event_name,
            event_class,
        )
    _EVENT_REGISTRY[event_name] = event_class
    logger.debug("Registered event: %s", event_name)
    return event_class


def get_event_class(event_name: str) -> type[DomainEvent] | None:
    """Get event class by name.

    Args:
        event_name: The event type name (e.g., "OrderCreatedEvent")

    Returns:
        The event class if registered, None otherwise

    Example:
        ```python
        event_class = get_event_class("OrderCreatedEvent")
        if event_class:
            event = event_class(**payload)
        ```
    """
    return _EVENT_REGISTRY.get(event_name)


def deserialize_event(event_type: str, payload: dict) -> DomainEvent:
    """Deserialize event from type name and payload.

    Args:
        event_type: The event type name (from OutboxRecord.type)
        payload: The event data (from OutboxRecord.payload)

    Returns:
        Deserialized domain event instance

    Raises:
        ValueError: If event type is not registered

    Example:
        ```python
        # From Outbox Projector
        event = deserialize_event(
            event_type="OrderCreatedEvent",
            payload={"order_id": "123", "customer_id": "456", ...}
        )
        ```
    """
    from bento.domain.domain_event import DomainEvent

    event_class = get_event_class(event_type)

    if event_class is None:
        logger.warning(
            "Event type %s not registered, falling back to base DomainEvent",
            event_type,
        )
        # Fallback to base DomainEvent
        event_class = DomainEvent

    try:
        # Handle UUID fields that might be strings in JSON
        from uuid import UUID

        if "event_id" in payload and isinstance(payload["event_id"], str):
            payload["event_id"] = UUID(payload["event_id"])

        # Handle datetime fields
        from datetime import datetime

        if "occurred_at" in payload and isinstance(payload["occurred_at"], str):
            payload["occurred_at"] = datetime.fromisoformat(
                payload["occurred_at"].replace("Z", "+00:00")
            )

        return event_class(**payload)
    except Exception as e:
        logger.error(
            "Failed to deserialize event %s: %s. Payload: %s",
            event_type,
            str(e),
            payload,
            exc_info=True,
        )
        raise ValueError(f"Failed to deserialize event {event_type}: {e}") from e


def get_all_registered_events() -> dict[str, type[DomainEvent]]:
    """Get all registered event classes.

    Returns:
        Dictionary of event_name -> event_class

    Example:
        ```python
        all_events = get_all_registered_events()
        print(f"Registered events: {list(all_events.keys())}")
        ```
    """
    return _EVENT_REGISTRY.copy()


def clear_registry() -> None:
    """Clear all registered events (mainly for testing).

    Example:
        ```python
        # In test teardown
        clear_registry()
        ```
    """
    _EVENT_REGISTRY.clear()
    logger.debug("Event registry cleared")
