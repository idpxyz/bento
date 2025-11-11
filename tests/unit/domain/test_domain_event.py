"""Unit tests for DomainEvent."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class TestCreatedEvent(DomainEvent):
    """Test domain event."""

    item_name: str = ""
    quantity: int = 0


@dataclass(frozen=True)
class TestUpdatedEvent(DomainEvent):
    """Another test domain event."""

    old_value: str = ""
    new_value: str = ""


class TestDomainEvent:
    """Test suite for DomainEvent."""

    def test_domain_event_creation(self):
        """Test creating a domain event."""
        event_id = uuid4()
        event = TestCreatedEvent(
            event_id=event_id,
            name="TestCreatedEvent",
            tenant_id="tenant-1",
            aggregate_id="agg-123",
            item_name="Widget",
            quantity=10,
        )

        assert event.event_id == event_id
        assert event.name == "TestCreatedEvent"
        assert event.tenant_id == "tenant-1"
        assert event.aggregate_id == "agg-123"
        assert event.item_name == "Widget"
        assert event.quantity == 10

    def test_domain_event_default_values(self):
        """Test domain event with default values."""
        event = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
        )

        assert event.event_id is not None
        assert event.name == "TestCreatedEvent"
        assert event.tenant_id is None
        assert event.aggregate_id is None
        assert event.schema_id is None
        assert event.schema_version == 1

    def test_domain_event_occurred_at(self):
        """Test that occurred_at is automatically set."""
        before = datetime.now(UTC)
        event = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
        )
        after = datetime.now(UTC)

        assert before <= event.occurred_at <= after

    def test_domain_event_is_immutable(self):
        """Test that domain events are immutable."""
        event = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
            item_name="Widget",
        )

        # Attempting to change field should raise an error
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            event.item_name = "New Widget"

    def test_domain_event_equality(self):
        """Test domain event equality."""
        event_id = uuid4()
        occurred_at = datetime.now(UTC)

        event1 = TestCreatedEvent(
            event_id=event_id,
            name="TestCreatedEvent",
            occurred_at=occurred_at,
            tenant_id="tenant-1",
            item_name="Widget",
            quantity=10,
        )

        event2 = TestCreatedEvent(
            event_id=event_id,
            name="TestCreatedEvent",
            occurred_at=occurred_at,
            tenant_id="tenant-1",
            item_name="Widget",
            quantity=10,
        )

        # Same data should be equal
        assert event1 == event2

    def test_domain_event_different_ids(self):
        """Test that events with different IDs are not equal."""
        event1 = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
            item_name="Widget",
        )

        event2 = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
            item_name="Widget",
        )

        # Different event_ids mean different events
        assert event1 != event2

    def test_domain_event_to_payload(self):
        """Test converting domain event to payload."""
        event = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
            tenant_id="tenant-1",
            aggregate_id="agg-123",
            item_name="Widget",
            quantity=10,
        )

        payload = event.to_payload()

        assert isinstance(payload, dict)
        assert payload["item_name"] == "Widget"
        assert payload["quantity"] == 10
        assert payload["tenant_id"] == "tenant-1"

    def test_domain_event_custom_schema(self):
        """Test domain event with custom schema information."""
        event = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
            schema_id="test.created.v2",
            schema_version=2,
            item_name="Widget",
        )

        assert event.schema_id == "test.created.v2"
        assert event.schema_version == 2

    def test_multiple_event_types(self):
        """Test creating different types of events."""
        created_event = TestCreatedEvent(
            event_id=uuid4(),
            name="TestCreatedEvent",
            item_name="Widget",
            quantity=5,
        )

        updated_event = TestUpdatedEvent(
            event_id=uuid4(),
            name="TestUpdatedEvent",
            old_value="old",
            new_value="new",
        )

        assert created_event.name == "TestCreatedEvent"
        assert updated_event.name == "TestUpdatedEvent"
        assert created_event != updated_event
