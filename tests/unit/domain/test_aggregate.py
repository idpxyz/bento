"""Unit tests for AggregateRoot."""

from dataclasses import dataclass
from uuid import uuid4

from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class MockEvent(DomainEvent):
    """Mock domain event for testing."""

    message: str = "test"


class MockAggregate(AggregateRoot):
    """Mock aggregate for testing."""

    def __init__(self, aggregate_id):
        super().__init__(aggregate_id)
        self.value = 0

    def increment(self):
        """Increment value and raise event."""
        self.value += 1
        self.add_event(
            MockEvent(
                event_id=uuid4(),
                topic="MockEvent",
                tenant_id="test",
                aggregate_id=str(self.id),
                message=f"Incremented to {self.value}",
            )
        )


class TestAggregateRoot:
    """Test suite for AggregateRoot."""

    def test_aggregate_initialization(self):
        """Test that aggregate can be initialized."""
        aggregate_id = "test-123"
        aggregate = MockAggregate(aggregate_id)

        assert aggregate.id == aggregate_id
        assert len(aggregate.events) == 0

    def test_add_event(self):
        """Test adding domain events."""
        aggregate = MockAggregate("test-123")
        event = MockEvent(
            event_id=uuid4(),
            topic="MockEvent",
            tenant_id="test",
            aggregate_id="test-123",
        )

        aggregate.add_event(event)

        assert len(aggregate.events) == 1
        assert aggregate.events[0] == event

    def test_add_multiple_events(self):
        """Test adding multiple events."""
        aggregate = MockAggregate("test-123")

        # Increment 3 times, should create 3 events
        aggregate.increment()
        aggregate.increment()
        aggregate.increment()

        assert len(aggregate.events) == 3
        assert aggregate.value == 3
        assert all(isinstance(e, MockEvent) for e in aggregate.events)

    def test_clear_events(self):
        """Test clearing domain events."""
        aggregate = MockAggregate("test-123")

        # Add some events
        aggregate.increment()
        aggregate.increment()
        assert len(aggregate.events) == 2

        # Clear events
        aggregate.clear_events()

        assert len(aggregate.events) == 0
        assert aggregate.value == 2  # Value should remain

    def test_events_property_returns_copy(self):
        """Test that events property returns a copy, not the original list."""
        aggregate = MockAggregate("test-123")
        aggregate.increment()

        events1 = aggregate.events
        events2 = aggregate.events

        # Should be equal but not the same object
        assert events1 == events2
        assert events1 is not events2

        # Modifying the returned list should not affect the aggregate
        events1.clear()
        assert len(aggregate.events) == 1

    def test_aggregate_inheritance_from_entity(self):
        """Test that AggregateRoot inherits from Entity."""
        from bento.domain.entity import Entity

        aggregate = MockAggregate("test-123")
        assert isinstance(aggregate, Entity)

    def test_event_order_preserved(self):
        """Test that events are stored in the order they were added."""
        aggregate = MockAggregate("test-123")

        event1 = MockEvent(
            event_id=uuid4(),
            topic="Event1",
            tenant_id="test",
            aggregate_id="test-123",
            message="first",
        )
        event2 = MockEvent(
            event_id=uuid4(),
            topic="Event2",
            tenant_id="test",
            aggregate_id="test-123",
            message="second",
        )
        event3 = MockEvent(
            event_id=uuid4(),
            topic="Event3",
            tenant_id="test",
            aggregate_id="test-123",
            message="third",
        )

        aggregate.add_event(event1)
        aggregate.add_event(event2)
        aggregate.add_event(event3)

        events = aggregate.events
        assert events[0].message == "first"
        assert events[1].message == "second"
        assert events[2].message == "third"
