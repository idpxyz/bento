"""Unit tests for Event Registry."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import (
    clear_registry,
    deserialize_event,
    get_all_registered_events,
    get_event_class,
    register_event,
)


@dataclass(frozen=True)
class UnregisteredEvent(DomainEvent):
    """Event that won't be registered."""

    data: str = ""


class TestEventRegistry:
    """Test suite for Event Registry."""

    def setup_method(self):
        """Clear registry before each test."""
        # Save current registry state
        from bento.domain.event_registry import get_all_registered_events

        self._saved_registry = get_all_registered_events().copy()
        clear_registry()

    def teardown_method(self):
        """Restore registry after each test."""
        clear_registry()
        # Restore saved events
        for event_class in self._saved_registry.values():
            register_event(event_class)

    def test_register_event(self):
        """Test registering an event."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            value: int = 0

        # Event should be in registry
        event_class = get_event_class("TestEvent")
        assert event_class is TestEvent

    def test_register_event_returns_class(self):
        """Test that register_event returns the class (decorator pattern)."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            value: int = 0

        # Should be able to instantiate the class
        event = TestEvent(
            event_id=uuid4(),
            name="TestEvent",
            value=42,
        )
        assert event.value == 42

    def test_register_multiple_events(self):
        """Test registering multiple events."""

        @register_event
        @dataclass(frozen=True)
        class Event1(DomainEvent):
            pass

        @register_event
        @dataclass(frozen=True)
        class Event2(DomainEvent):
            pass

        assert get_event_class("Event1") is Event1
        assert get_event_class("Event2") is Event2

    def test_register_event_duplicate_warning(self, caplog):
        """Test that registering duplicate event logs warning."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            version: int = 1

        # Register again with same name but different class
        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):  # noqa: F811
            version: int = 2

        # Should log warning
        assert "already registered" in caplog.text

        # Should use the latest registration
        event_class = get_event_class("TestEvent")
        event = event_class(event_id=uuid4(), name="TestEvent")
        assert event.version == 2

    def test_get_event_class_not_found(self):
        """Test getting event class that doesn't exist."""
        result = get_event_class("NonExistentEvent")
        assert result is None

    def test_get_all_registered_events(self):
        """Test getting all registered events."""

        @register_event
        @dataclass(frozen=True)
        class Event1(DomainEvent):
            pass

        @register_event
        @dataclass(frozen=True)
        class Event2(DomainEvent):
            pass

        all_events = get_all_registered_events()

        assert len(all_events) == 2
        assert "Event1" in all_events
        assert "Event2" in all_events
        assert all_events["Event1"] is Event1
        assert all_events["Event2"] is Event2

    def test_get_all_registered_events_returns_copy(self):
        """Test that get_all_registered_events returns a copy."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            pass

        all_events = get_all_registered_events()

        # Modifying the returned dict should not affect registry
        all_events.clear()

        # Registry should still have the event
        assert get_event_class("TestEvent") is TestEvent

    def test_clear_registry(self):
        """Test clearing the registry."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            pass

        assert get_event_class("TestEvent") is TestEvent

        clear_registry()

        assert get_event_class("TestEvent") is None
        assert len(get_all_registered_events()) == 0

    def test_deserialize_event(self):
        """Test deserializing an event."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            value: int = 0
            message: str = ""

        event_id = uuid4()
        occurred_at = datetime.now(UTC)

        payload = {
            "event_id": str(event_id),
            "name": "TestEvent",
            "occurred_at": occurred_at.isoformat(),
            "tenant_id": "tenant-1",
            "aggregate_id": "agg-123",
            "schema_id": None,
            "schema_version": 1,
            "value": 42,
            "message": "Hello",
        }

        event = deserialize_event("TestEvent", payload)

        assert isinstance(event, TestEvent)
        assert event.event_id == event_id
        assert event.value == 42
        assert event.message == "Hello"
        assert event.tenant_id == "tenant-1"

    def test_deserialize_event_with_uuid_object(self):
        """Test deserializing event when UUID is already an object."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            pass

        event_id = uuid4()
        payload = {
            "event_id": event_id,  # Already a UUID object
            "name": "TestEvent",
        }

        event = deserialize_event("TestEvent", payload)
        assert event.event_id == event_id

    def test_deserialize_event_unregistered_type(self, caplog):
        """Test deserializing unregistered event type falls back to base."""
        event_id = uuid4()
        payload = {
            "event_id": str(event_id),
            "name": "UnknownEvent",
        }

        event = deserialize_event("UnknownEvent", payload)

        # Should fall back to base DomainEvent
        assert isinstance(event, DomainEvent)
        assert event.name == "UnknownEvent"
        assert "not registered" in caplog.text

    def test_deserialize_event_with_datetime_string(self):
        """Test deserializing event with datetime as string."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            pass

        occurred_at = datetime.now(UTC)
        payload = {
            "event_id": str(uuid4()),
            "name": "TestEvent",
            "occurred_at": occurred_at.isoformat(),
        }

        event = deserialize_event("TestEvent", payload)

        # Should parse the datetime string
        assert isinstance(event.occurred_at, datetime)
        # Allow small time difference due to microsecond precision
        assert abs((event.occurred_at - occurred_at).total_seconds()) < 0.001

    def test_deserialize_event_with_z_timezone(self):
        """Test deserializing datetime with Z (Zulu) timezone."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            pass

        payload = {
            "event_id": str(uuid4()),
            "name": "TestEvent",
            "occurred_at": "2025-01-01T12:00:00.000Z",
        }

        event = deserialize_event("TestEvent", payload)

        assert isinstance(event.occurred_at, datetime)
        assert event.occurred_at.tzinfo == UTC

    def test_deserialize_event_invalid_payload_raises(self):
        """Test that invalid payload raises ValueError."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            value: int = 0

            def __post_init__(self):
                # Add validation that will fail
                if self.value < 10:
                    raise ValueError("value must be >= 10")

        payload = {
            "event_id": str(uuid4()),
            "name": "TestEvent",
            "value": 5,  # Will fail validation
        }

        with pytest.raises(ValueError, match="Failed to deserialize event TestEvent"):
            deserialize_event("TestEvent", payload)

    def test_deserialize_event_invalid_uuid(self):
        """Test that invalid UUID string raises ValueError."""

        @register_event
        @dataclass(frozen=True)
        class TestEvent(DomainEvent):
            pass

        payload = {
            "event_id": "not-a-valid-uuid",
            "name": "TestEvent",
        }

        with pytest.raises(ValueError, match="Failed to deserialize event"):
            deserialize_event("TestEvent", payload)

    def test_deserialize_complex_event(self):
        """Test deserializing event with complex data types."""

        @register_event
        @dataclass(frozen=True)
        class OrderCreatedEvent(DomainEvent):
            order_id: str = ""
            customer_id: str = ""
            total_amount: float = 0.0
            items: list = None

            def __post_init__(self):
                if self.items is None:
                    object.__setattr__(self, "items", [])

        payload = {
            "event_id": str(uuid4()),
            "name": "OrderCreatedEvent",
            "order_id": "ord-123",
            "customer_id": "cust-456",
            "total_amount": 99.99,
            "items": ["item1", "item2"],
        }

        event = deserialize_event("OrderCreatedEvent", payload)

        assert isinstance(event, OrderCreatedEvent)
        assert event.order_id == "ord-123"
        assert event.total_amount == 99.99
        assert event.items == ["item1", "item2"]

    def test_registry_isolation_between_tests(self):
        """Test that registry is properly isolated between tests."""
        # This test verifies that setup_method/teardown_method work
        all_events = get_all_registered_events()
        assert len(all_events) == 0  # Should be empty due to setup_method
