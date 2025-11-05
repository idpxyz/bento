"""EventPublisher Port - Domain layer contract for publishing events.

This module defines the EventPublisher protocol for publishing domain events
to external systems (message queues, event buses, etc.).

Domain events represent significant state changes in the domain and enable
decoupling through eventual consistency.
"""

from typing import Protocol

from bento.domain.domain_event import DomainEvent


class EventPublisher(Protocol):
    """EventPublisher protocol - defines the contract for event publishing.

    This protocol abstracts the event publishing mechanism, allowing the
    domain layer to emit events without depending on specific message
    broker implementations (Pulsar, Kafka, Redis, etc.).

    This is a Protocol (not ABC), enabling structural subtyping.

    Example:
        ```python
        # Domain layer uses the protocol
        class UserService:
            def __init__(self, publisher: EventPublisher):
                self.publisher = publisher

            async def create_user(self, ...):
                user = User.create(...)
                event = UserCreatedEvent(user_id=user.id, ...)
                await self.publisher.publish(event)

        # Infrastructure provides implementation
        class PulsarEventPublisher:
            async def publish(self, event: DomainEvent) -> None:
                # Pulsar-specific implementation
                ...
        ```
    """

    async def publish(self, event: DomainEvent) -> None:
        """Publish a single domain event.

        The implementation should:
        1. Serialize the event to the appropriate format
        2. Send it to the configured message broker/bus
        3. Handle transient failures with retries
        4. Ensure at-least-once delivery semantics

        Args:
            event: The domain event to publish

        Raises:
            May raise infrastructure errors that should be handled
            by the application layer

        Example:
            ```python
            event = UserCreatedEvent(
                event_id="evt-123",
                user_id="user-456",
                email="alice@example.com",
                occurred_at=datetime.utcnow()
            )
            await publisher.publish(event)
            ```
        """
        ...

    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish multiple domain events in batch.

        This method is useful when publishing events collected from
        aggregates during a Unit of Work commit.

        The implementation should:
        1. Maintain event ordering if required
        2. Handle partial failures appropriately
        3. Optimize for batch operations when possible

        Args:
            events: List of domain events to publish

        Example:
            ```python
            events = [
                UserCreatedEvent(...),
                WelcomeEmailSentEvent(...),
                UserActivatedEvent(...),
            ]
            await publisher.publish_all(events)
            ```
        """
        ...
