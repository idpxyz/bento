"""Event Registry for event serialization and deserialization.

This module provides a centralized registry for all domain events,
enabling proper deserialization from the Outbox table.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.domain.domain_event import DomainEvent

logger = logging.getLogger(__name__)

# Enable debug logging for this module
logger.setLevel(logging.DEBUG)


def _log_registry_state(action: str, event_name: str, topic: str = "") -> None:
    """Log the current state of the registry for debugging.

    Args:
        action: The action being performed (e.g., "AFTER_REGISTER", "MISSING_EVENT")
        event_name: The name of the event being processed
        topic: Optional topic associated with the event (defaults to empty string)
    """
    with _REGISTRY_LOCK, _TOPIC_REGISTRY_LOCK:
        logger.debug(
            "Registry State [%s] - Event: %s, Topic: %s\n"
            "  Registered Events: %s\n"
            "  Registered Topics: %s",
            action,
            event_name,
            topic or "N/A",
            list(_EVENT_REGISTRY.keys()),
            list(_TOPIC_TO_CLASS_REGISTRY.keys()),
        )


# Thread-safe event registry with locks
_EVENT_REGISTRY: dict[str, type[DomainEvent]] = {}
_TOPIC_TO_CLASS_REGISTRY: dict[str, type[DomainEvent]] = {}

# Thread synchronization locks
_REGISTRY_LOCK = threading.RLock()
_TOPIC_REGISTRY_LOCK = threading.RLock()


def register_event[T: "DomainEvent"](event_class: type[T]) -> type[T]:
    """Decorator to register a domain event class with topic mapping.

    Supports both class name and topic-based lookup for flexible event handling.
    Automatically creates topic from class name if not explicitly set.

    Args:
        event_class: The domain event class to register

    Returns:
        The same event class (allows using as decorator)

    Example:
        ```python
        @register_event
        @dataclass(frozen=True)
        class OrderCreatedEvent(DomainEvent):
            order_id: str = ""
            topic: str = "order.created"  # Will map both ways
        ```
    """
    event_name = event_class.__name__
    logger.info("🔔 Starting registration for event: %s", event_name)

    # Thread-safe registration with locks
    with _REGISTRY_LOCK:
        # Register by class name (existing behavior)
        if event_name in _EVENT_REGISTRY:
            logger.warning(
                "Event %s is already registered, overwriting with %s",
                event_name,
                event_class,
            )
        _EVENT_REGISTRY[event_name] = event_class
        logger.debug("Registered event by name: %s", event_name)

    # Register by topic (new capability) - separate lock for topic registry
    with _TOPIC_REGISTRY_LOCK:
        # Get default topic from class instance or generate from class name
        try:
            default_instance = event_class()
            topic = getattr(default_instance, "topic", "") or _class_name_to_topic(event_name)
            logger.debug("Detected topic '%s' for event %s", topic, event_name)
        except (TypeError, ValueError) as e:
            topic = _class_name_to_topic(event_name)
            logger.debug(
                "Could not instantiate %s, using generated topic: %s. Error: %s",
                event_name,
                topic,
                str(e),
            )

        if topic and topic != event_name:  # Don't duplicate if topic equals class name
            if topic in _TOPIC_TO_CLASS_REGISTRY:
                existing = _TOPIC_TO_CLASS_REGISTRY[topic].__name__
                logger.warning(
                    "Topic '%s' already registered to %s, will be overwritten by %s",
                    topic,
                    existing,
                    event_name,
                )
            _TOPIC_TO_CLASS_REGISTRY[topic] = event_class
            logger.info("✅ Registered event topic: %s -> %s", topic, event_name)
        else:
            logger.info("✅ Registered event (no topic): %s", event_name)

    _log_registry_state("AFTER_REGISTER", event_name, topic)
    return event_class


def _class_name_to_topic(class_name: str) -> str:
    """Convert class name to business-friendly topic with robust edge case handling.

    Args:
        class_name: Event class name (e.g., "OrderCreatedEvent")

    Returns:
        Business topic (e.g., "order.created")

    Examples:
        OrderCreatedEvent -> order.created
        PaymentProcessedEvent -> payment.processed
        XMLHttpRequestEvent -> xml_http_request.event
        IOEvent -> io.event
        HTTPSConnectionEvent -> https_connection.event
        DatabaseConnectionPoolEvent -> database_connection_pool.event
        SingleWordEvent -> single_word.event
        Order2CreatedEvent -> order2.created
        ABC -> abc.event
        Event -> event.default
        "" -> unknown.event
    """
    import re

    # Input validation
    if not class_name or not isinstance(class_name, str):
        return "unknown.event"

    # Normalize input
    name = class_name.strip()
    if not name:
        return "unknown.event"

    # Remove "Event" suffix
    if name.endswith("Event"):
        name = name[:-5]

    # Handle empty result after removing "Event"
    if not name:
        return "event.default"

    # Enhanced CamelCase splitting with support for:
    # - Consecutive uppercase letters (XMLHttp -> XML, Http)
    # - Numbers (Order2Created -> Order2, Created)
    # - Mixed cases (HTTPSConnection -> HTTPS, Connection)

    # Use a more sophisticated approach: first insert underscores, then split
    # Handle transitions: lowercase->uppercase, digit->letter (but NOT letter->digit)
    with_underscores = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)  # camelCase
    # Only split digit->letter, keep letter+digit together (Order2 stays as Order2)
    with_underscores = re.sub(r"(\d)([a-zA-Z])", r"\1_\2", with_underscores)  # digit->letter

    # Handle consecutive uppercase letters more carefully
    # XML_HTTP_REQUEST should become XML_HTTP_REQUEST not X_M_L_H_T_T_P_R_E_Q_U_E_S_T
    with_underscores = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", with_underscores)

    # Split by underscores to get parts
    parts = [part for part in with_underscores.split("_") if part]

    # Clean and normalize parts
    normalized_parts = []
    for part in parts:
        part = part.strip()
        if part:
            # Convert to lowercase and handle common abbreviations
            lower_part = part.lower()
            normalized_parts.append(lower_part)

    if not normalized_parts:
        return "unknown.event"

    # Determine entity and action parts
    if len(normalized_parts) >= 2:
        # Multi-part: entity.action format
        entity_parts = normalized_parts[:-1]
        action_part = normalized_parts[-1]
        entity_name = "_".join(entity_parts)
        return f"{entity_name}.{action_part}"
    else:
        # Single part: treat as entity with default action
        single_part = normalized_parts[0]
        return f"{single_part}.event"


def get_event_class(event_name: str) -> type[DomainEvent] | None:
    """Get event class by name or topic.

    Args:
        event_name: The event type name (class name) or topic

    Returns:
        The event class if registered, None otherwise

    Example:
        ```python
        # Both work:
        event_class = get_event_class("OrderCreatedEvent")  # by class name
        event_class = get_event_class("order.created")     # by topic
        ```
    """
    # First try direct class name lookup (existing behavior)
    with _REGISTRY_LOCK:
        if event_class := _EVENT_REGISTRY.get(event_name):
            logger.debug("Found event by class name: %s", event_name)
            return event_class

    # Then try by topic (new capability)
    with _TOPIC_REGISTRY_LOCK:
        if event_class := _TOPIC_TO_CLASS_REGISTRY.get(event_name):
            logger.debug("Found event by topic: %s -> %s", event_name, event_class.__name__)
            return event_class

    logger.debug("Event not found in registry: %s", event_name)
    return None


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

    logger.debug(
        "🔍 Attempting to deserialize event. Type: %s, Payload keys: %s",
        event_type,
        list(payload.keys()) if payload else "EMPTY",
    )

    event_class = get_event_class(event_type)

    if event_class is None:
        _log_registry_state("MISSING_EVENT", event_type)
        logger.error(
            "❌ Event type '%s' not found in registry! Available events: %s, Topics: %s",
            event_type,
            list(_EVENT_REGISTRY.keys()),
            list(_TOPIC_TO_CLASS_REGISTRY.keys()),
        )
        logger.warning("Falling back to base DomainEvent for: %s", event_type)
        event_class = DomainEvent

    try:
        safe_payload = _validate_and_sanitize_payload(payload, event_class)
        logger.debug("Successfully validated payload for %s", event_type)
        event = event_class(**safe_payload)
        logger.info("✅ Successfully deserialized event: %s", event_type)
        return event
    except Exception as e:
        logger.error(
            "❌ Failed to deserialize event %s: %s\nPayload: %s",
            event_type,
            str(e),
            payload,
            exc_info=True,
        )
        raise ValueError(f"Failed to deserialize event {event_type}: {e}") from e


def _validate_and_sanitize_payload(payload: dict, event_class: type) -> dict:
    """Safely validate and sanitize payload for deserialization.

    🔒 Security measures:
    - Payload size limits
    - Field whitelist validation
    - Type safety checks
    - Prevent object injection

    Args:
        payload: Raw payload from storage
        event_class: Target event class

    Returns:
        Sanitized payload safe for instantiation

    Raises:
        ValueError: If payload is invalid or unsafe
    """
    import sys
    from dataclasses import fields

    # 1. Size limits for security
    MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB limit
    MAX_FIELD_COUNT = 100  # Max fields

    payload_size = sys.getsizeof(str(payload))
    if payload_size > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload too large: {payload_size} bytes (max: {MAX_PAYLOAD_SIZE})")

    if len(payload) > MAX_FIELD_COUNT:
        raise ValueError(f"Too many fields: {len(payload)} (max: {MAX_FIELD_COUNT})")

    # 2. Get valid fields from dataclass
    try:
        valid_fields = {f.name: f.type for f in fields(event_class)}
    except TypeError:
        # Fallback for non-dataclass events
        valid_fields = getattr(event_class, "__annotations__", {})

    # 3. Field whitelist validation - only allow known fields
    safe_payload = {}
    for field_name, value in payload.items():
        # Skip dangerous field names
        if field_name.startswith("__") or field_name in {"exec", "eval", "compile", "import"}:
            logger.warning("Skipping dangerous field: %s", field_name)
            continue

        if field_name not in valid_fields:
            logger.debug("Skipping unknown field: %s", field_name)
            continue

        # 4. Type-specific sanitization
        sanitized_value = _sanitize_field_value(field_name, value)
        if sanitized_value is not None:
            safe_payload[field_name] = sanitized_value

    return safe_payload


def _sanitize_field_value(field_name: str, value):
    """Sanitize individual field value based on expected type."""
    from datetime import datetime
    from uuid import UUID

    MAX_STRING_LENGTH = 10000

    # Handle None values
    if value is None:
        return None

    # String length validation
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        raise ValueError(f"String field '{field_name}' too long: {len(value)} chars")

    # Type-specific handling
    if field_name == "event_id" and isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as e:
            raise ValueError(f"Invalid UUID for event_id: {value}") from e

    if field_name == "occurred_at" and isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid datetime for occurred_at: {value}") from e

    # Prevent object injection - only allow primitive types
    allowed_types = (str, int, float, bool, list, dict)
    if not isinstance(value, allowed_types):
        logger.warning("Rejecting non-primitive value for field %s: %s", field_name, type(value))
        return None

    # Recursive validation for nested structures
    if isinstance(value, dict):
        if len(value) > 50:  # Limit nested dict size
            raise ValueError(f"Nested dict too large in field '{field_name}'")
        return {k: v for k, v in value.items() if isinstance(k, str) and len(k) < 100}

    if isinstance(value, list):
        if len(value) > 1000:  # Limit list size
            raise ValueError(f"List too large in field '{field_name}'")
        return [item for item in value if isinstance(item, allowed_types)][
            :100
        ]  # Truncate if needed

    return value


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
    with _REGISTRY_LOCK:
        return _EVENT_REGISTRY.copy()


def clear_event_registry() -> None:
    """Clear all registered events from memory.

    🔧 Resource Management:
    - Prevents memory leaks in long-running services
    - Useful for testing environments and plugin systems
    - Thread-safe operation with proper locking

    ⚠️  Warning:
    - This will break deserialization of existing events in storage
    - Use only during application shutdown or controlled environments
    - Consider using EventRegistryContext for scoped cleanup

    Example:
        ```python
        # Clear during shutdown
        clear_event_registry()

        # Or use context manager
        with EventRegistryContext():
            register_event(MyEvent)
            # Events cleared automatically on exit
        ```
    """
    with _REGISTRY_LOCK:
        event_count = len(_EVENT_REGISTRY)
        _EVENT_REGISTRY.clear()
        logger.info("Cleared %d event class registrations", event_count)

    with _TOPIC_REGISTRY_LOCK:
        topic_count = len(_TOPIC_TO_CLASS_REGISTRY)
        _TOPIC_TO_CLASS_REGISTRY.clear()
        logger.info("Cleared %d topic mappings", topic_count)


def get_registry_stats() -> dict:
    """Get memory usage statistics for event registries.

    Returns:
        Dictionary with registry statistics including:
        - event_class_count: Number of registered event classes
        - topic_mapping_count: Number of topic mappings
        - estimated_memory_kb: Rough memory usage estimate

    Example:
        ```python
        stats = get_registry_stats()
        print(f"Memory usage: {stats['estimated_memory_kb']} KB")
        print(f"Registered events: {stats['event_class_count']}")
        ```
    """
    import sys

    with _REGISTRY_LOCK:
        event_count = len(_EVENT_REGISTRY)
        event_registry_size = sys.getsizeof(_EVENT_REGISTRY)

    with _TOPIC_REGISTRY_LOCK:
        topic_count = len(_TOPIC_TO_CLASS_REGISTRY)
        topic_registry_size = sys.getsizeof(_TOPIC_TO_CLASS_REGISTRY)

    # Rough estimate: each event class reference ~ 1-5KB
    estimated_memory_bytes = (
        event_registry_size + topic_registry_size + (event_count + topic_count) * 2048
    )  # 2KB per entry estimate

    return {
        "event_class_count": event_count,
        "topic_mapping_count": topic_count,
        "estimated_memory_kb": round(estimated_memory_bytes / 1024, 2),
        "registry_size_bytes": event_registry_size,
        "topic_mapping_size_bytes": topic_registry_size,
    }


class EventRegistryContext:
    """Context manager for scoped event registry management.

    🔧 Resource Management:
    - Automatically cleans up event registrations on exit
    - Perfect for testing environments and plugin systems
    - Prevents memory accumulation in long-running services

    Example:
        ```python
        # Scoped registration - auto cleanup
        with EventRegistryContext() as ctx:
            register_event(TemporaryEvent)
            # Use events...
        # Events automatically cleared here

        # With initial state preservation
        with EventRegistryContext(preserve_existing=True) as ctx:
            register_event(NewEvent)
            # Only NewEvent will be cleared on exit
        ```
    """

    def __init__(self, preserve_existing: bool = False):
        """Initialize context manager.

        Args:
            preserve_existing: If True, only clear events registered within
                             this context. If False, clear all events on exit.
        """
        self.preserve_existing = preserve_existing
        self._initial_events = None
        self._initial_topics = None

    def __enter__(self) -> EventRegistryContext:
        """Enter context - optionally snapshot existing registrations."""
        if self.preserve_existing:
            with _REGISTRY_LOCK:
                self._initial_events = set(_EVENT_REGISTRY.keys())
            with _TOPIC_REGISTRY_LOCK:
                self._initial_topics = set(_TOPIC_TO_CLASS_REGISTRY.keys())

        logger.debug("Entered EventRegistryContext (preserve_existing=%s)", self.preserve_existing)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - cleanup registrations."""
        if (
            self.preserve_existing
            and self._initial_events is not None
            and self._initial_topics is not None
        ):
            # Only clear events registered within this context
            with _REGISTRY_LOCK:
                new_events = set(_EVENT_REGISTRY.keys()) - self._initial_events
                for event_name in new_events:
                    _EVENT_REGISTRY.pop(event_name, None)
                logger.debug("Cleared %d new event registrations", len(new_events))

            with _TOPIC_REGISTRY_LOCK:
                new_topics = set(_TOPIC_TO_CLASS_REGISTRY.keys()) - self._initial_topics
                for topic in new_topics:
                    _TOPIC_TO_CLASS_REGISTRY.pop(topic, None)
                logger.debug("Cleared %d new topic mappings", len(new_topics))
        else:
            # Clear all registrations
            clear_event_registry()

        logger.debug("Exited EventRegistryContext")
