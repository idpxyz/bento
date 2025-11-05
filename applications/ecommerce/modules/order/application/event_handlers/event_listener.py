"""Event listener for order events.

This module demonstrates how to integrate the Outbox pattern with event handlers.
It shows best practices for:
- Event routing
- Error handling
- Idempotency
"""

import logging
from collections.abc import Callable

from applications.ecommerce.modules.order.application.event_handlers.order_event_handler import (
    OrderEventHandler,
)
from bento.domain.domain_event import DomainEvent

logger = logging.getLogger(__name__)


class OrderEventListener:
    """Event listener that routes events to handlers.

    This class demonstrates:
    - Integration between Outbox Projector and Event Handlers
    - Event routing based on event type
    - Error handling and logging

    Best Practices:
    - Implements simplified MessageBus interface for Outbox integration
    - Delegates to specific handlers for separation of concerns
    - Logs all events for observability
    - Handles errors gracefully

    Note: This is a simplified implementation focused on event handling.
    For production, you would integrate with a full message broker (Pulsar, Kafka, etc.).
    """

    def __init__(self) -> None:
        """Initialize the event listener."""
        self._order_handler = OrderEventHandler()
        logger.info("OrderEventListener initialized")

    async def publish(self, event: DomainEvent | list[DomainEvent]) -> None:
        """Publish event(s) to appropriate handler.

        This method is called by the Outbox Projector when events
        are ready to be published.

        Args:
            event: Domain event or list of events to publish

        Best Practice:
        - Log event for observability
        - Route to appropriate handler
        - Handle both single and batch publishing
        """
        # Handle batch publishing
        if isinstance(event, list):
            await self.publish_batch(event)
            return

        # Handle single event
        event_name = event.name or event.__class__.__name__

        logger.info(
            f"📨 Publishing event: {event_name}",
            extra={
                "event_id": str(event.event_id),
                "event_name": event_name,
                "tenant_id": event.tenant_id,
                "aggregate_id": event.aggregate_id,
            },
        )

        try:
            # Route to order handler
            # In a larger system, you would have multiple handlers
            # and route based on event type
            await self._order_handler.handle(event)

            logger.debug(
                f"✅ Successfully published event: {event_name}",
                extra={"event_id": str(event.event_id)},
            )

        except Exception as e:
            # Log error but don't raise - let Outbox Projector handle retries
            logger.error(
                f"❌ Error publishing event {event_name}: {e}",
                exc_info=True,
                extra={
                    "event_id": str(event.event_id),
                    "event_name": event_name,
                },
            )
            # Re-raise to trigger Outbox retry mechanism
            raise

    async def publish_batch(self, events: list[DomainEvent]) -> None:
        """Publish multiple events in batch.

        Args:
            events: List of domain events to publish

        Best Practice:
        - Process events individually for better error isolation
        - Log batch statistics
        """
        logger.info(f"📦 Publishing batch of {len(events)} events")

        success_count = 0
        error_count = 0

        for event in events:
            try:
                await self.publish(event)
                success_count += 1
            except Exception:
                error_count += 1

        logger.info(
            f"✅ Batch processing complete: {success_count} succeeded, {error_count} failed"
        )

    # Optional: Implement other MessageBus protocol methods for compatibility

    async def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Subscribe to event type (not implemented in this simplified version)."""
        logger.warning("Subscribe not implemented in OrderEventListener")

    async def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Unsubscribe from event type (not implemented)."""
        logger.warning("Unsubscribe not implemented in OrderEventListener")

    async def start(self) -> None:
        """Start the listener (not needed for this implementation)."""
        logger.info("OrderEventListener started")

    async def stop(self) -> None:
        """Stop the listener (not needed for this implementation)."""
        logger.info("OrderEventListener stopped")


def create_event_listener() -> OrderEventListener:
    """Factory function to create event listener.

    Returns:
        Configured event listener instance

    Best Practice:
    - Use factory functions for dependency injection
    - Allows easy testing with mocks
    - Centralizes configuration
    """
    return OrderEventListener()
