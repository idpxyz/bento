"""MessageBus Port - Application layer contract for message/event bus.

This module defines the MessageBus protocol for publishing and subscribing
to domain events across service boundaries.

Message Bus enables:
1. Asynchronous event-driven architecture
2. Service decoupling
3. Scalable event processing
"""

from collections.abc import Callable
from typing import Protocol

from bento.domain.domain_event import DomainEvent


class MessageBus(Protocol):
    """MessageBus protocol - defines the contract for message/event bus operations.

    This protocol abstracts message bus mechanisms, allowing the application
    layer to publish and subscribe to events without depending on specific
    implementations (Pulsar, Kafka, Redis, RabbitMQ, etc.).

    This is a Protocol (not ABC), enabling structural subtyping.

    Example:
        ```python
        # Publishing events
        class OrderService:
            def __init__(self, bus: MessageBus):
                self.bus = bus

            async def create_order(self, ...):
                order = Order.create(...)
                event = OrderCreatedEvent(order_id=order.id, ...)
                await self.bus.publish(event)

        # Subscribing to events
        async def handle_order_created(event: OrderCreatedEvent):
            print(f"Order created: {event.order_id}")
            # Send confirmation email, update inventory, etc.

        await bus.subscribe(OrderCreatedEvent, handle_order_created)

        # Infrastructure provides implementation
        class PulsarMessageBus:
            async def publish(self, event: DomainEvent) -> None:
                # Pulsar-specific implementation
                ...
        ```
    """

    async def publish(self, event: DomainEvent | list[DomainEvent]) -> None:
        """Publish domain event(s) to the message bus.

        The implementation should:
        1. Serialize the event(s)
        2. Determine the topic/channel from event type
        3. Send to the message broker
        4. Handle transient failures with retries

        Supports both single event and batch publishing for performance.

        Args:
            event: The domain event or list of events to publish

        Raises:
            May raise infrastructure errors that should be handled
            by the application layer

        Example:
            ```python
            # Single event
            event = OrderCreatedEvent(
                event_id="evt-123",
                order_id="order-456",
                customer_id="cust-789",
                total_amount=99.99,
                occurred_at=datetime.utcnow()
            )
            await bus.publish(event)

            # Batch publish
            events = [event1, event2, event3]
            await bus.publish(events)
            ```
        """
        ...

    async def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Subscribe to a specific event type.

        The implementation should:
        1. Register the handler for the event type
        2. Set up subscription to the appropriate topic/channel
        3. Deserialize incoming events
        4. Invoke the handler for matching events

        Args:
            event_type: The event class to subscribe to
            handler: Async function to handle the event

        Note:
            The handler should be idempotent as events may be delivered
            more than once (at-least-once delivery semantics).

        Example:
            ```python
            async def handle_order_created(event: OrderCreatedEvent):
                # Process the event
                logger.info(f"Processing order: {event.order_id}")
                await send_confirmation_email(event.customer_id)

            await bus.subscribe(OrderCreatedEvent, handle_order_created)
            ```
        """
        ...

    async def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: The event class to unsubscribe from
            handler: The handler function to remove

        Example:
            ```python
            await bus.unsubscribe(OrderCreatedEvent, handle_order_created)
            ```
        """
        ...

    async def start(self) -> None:
        """Start the message bus (begin consuming messages).

        This method should:
        1. Connect to the message broker
        2. Start consumer(s) for subscribed topics
        3. Begin processing incoming events

        Usually called during application startup.

        Example:
            ```python
            # In startup lifecycle
            await bus.start()
            ```
        """
        ...

    async def stop(self) -> None:
        """Stop the message bus (stop consuming messages).

        This method should:
        1. Stop all consumers gracefully
        2. Wait for in-flight messages to complete
        3. Disconnect from the message broker

        Usually called during application shutdown.

        Example:
            ```python
            # In shutdown lifecycle
            await bus.stop()
            ```
        """
        ...
