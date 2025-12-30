"""Order event handler.

This module demonstrates event-driven architecture best practices:
- Decoupling business logic through events
- Side effect orchestration
- Integration with external systems
"""

import logging

from applications.ecommerce.modules.order.domain.events import (
    OrderCancelled,
    OrderCreated,
    OrderPaid,
)
from bento.domain.domain_event import DomainEvent

logger = logging.getLogger(__name__)


class OrderEventHandler:
    """Handle order domain events.

    This handler demonstrates:
    - Event-driven architecture
    - Separation of concerns
    - Integration points for external systems

    Best Practices:
    - Handlers should be idempotent (can be called multiple times safely)
    - Each handler does one thing well
    - Failures are logged but don't block event processing
    """

    def __init__(self) -> None:
        """Initialize the event handler."""
        self._handlers = {
            "OrderCreated": self._handle_order_created,
            "OrderPaid": self._handle_order_paid,
            "OrderCancelled": self._handle_order_cancelled,
        }

    async def handle(self, event: DomainEvent) -> None:
        """Route events to specific handlers.

        Args:
            event: Domain event to handle
        """
        event_name = event.topic or event.__class__.__name__
        handler = self._handlers.get(event_name)

        if handler:
            try:
                await handler(event)
            except Exception as e:
                # Log but don't raise - events should be idempotent
                logger.error(
                    f"Error handling {event_name}: {e}",
                    exc_info=True,
                    extra={
                        "event_id": str(event.event_id),
                        "event_name": event_name,
                    },
                )
        else:
            logger.debug(f"No handler found for event: {event_name}")

    async def _handle_order_created(self, event: OrderCreated) -> None:
        """Handle OrderCreated event.

        Best Practice: This demonstrates how to trigger multiple side effects
        when an order is created:
        - Send confirmation email
        - Reserve inventory
        - Notify warehouse
        - Create analytics record

        Args:
            event: OrderCreated event
        """
        logger.info(
            f"📦 Order created: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": str(event.order_id),
                "customer_id": str(event.customer_id),
                "total_amount": event.total_amount,
            },
        )

        # Simulate sending confirmation email
        await self._send_order_confirmation_email(event)

        # Simulate reserving inventory
        await self._reserve_inventory(event)

        # Simulate notifying warehouse
        await self._notify_warehouse(event)

        logger.info(f"✅ Finished processing OrderCreated for order {event.order_id}")

    async def _handle_order_paid(self, event: OrderPaid) -> None:
        """Handle OrderPaid event.

        Best Practice: Payment triggers fulfillment workflow
        - Send payment receipt
        - Initiate fulfillment process
        - Update analytics

        Args:
            event: OrderPaid event
        """
        logger.info(
            f"💳 Order paid: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": str(event.order_id),
                "customer_id": str(event.customer_id),
                "total_amount": event.total_amount,
            },
        )

        # Simulate sending payment receipt
        await self._send_payment_receipt(event)

        # Simulate initiating fulfillment
        await self._initiate_fulfillment(event)

        # Simulate updating analytics
        await self._update_payment_analytics(event)

        logger.info(f"✅ Finished processing OrderPaid for order {event.order_id}")

    async def _handle_order_cancelled(self, event: OrderCancelled) -> None:
        """Handle OrderCancelled event.

        Best Practice: Cancellation triggers cleanup workflow
        - Send cancellation email
        - Release inventory
        - Process refund (if paid)

        Args:
            event: OrderCancelled event
        """
        logger.info(
            f"❌ Order cancelled: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": str(event.order_id),
                "customer_id": str(event.customer_id),
                "reason": event.reason,
            },
        )

        # Simulate sending cancellation email
        await self._send_cancellation_email(event)

        # Simulate releasing inventory
        await self._release_inventory(event)

        # Simulate processing refund if order was paid
        await self._process_refund_if_needed(event)

        logger.info(f"✅ Finished processing OrderCancelled for order {event.order_id}")

    # Simulated integration methods - In production, these would call real services

    async def _send_order_confirmation_email(self, event: OrderCreated) -> None:
        """Send order confirmation email (simulated).

        In production, this would integrate with:
        - Email service (SendGrid, AWS SES, etc.)
        - Template engine
        - Customer preference system
        """
        logger.info(f"📧 Sending order confirmation email to customer {event.customer_id}")
        # TODO: Integrate with email service

    async def _reserve_inventory(self, event: OrderCreated) -> None:
        """Reserve inventory for order items (simulated).

        In production, this would:
        - Call inventory service
        - Handle insufficient stock scenarios
        - Support distributed transactions/sagas
        """
        logger.info(f"📦 Reserving inventory for order {event.order_id} (${event.total_amount})")
        # TODO: Integrate with inventory service

    async def _notify_warehouse(self, event: OrderCreated) -> None:
        """Notify warehouse of new order (simulated).

        In production, this would:
        - Call warehouse management system
        - Trigger pick/pack workflow
        - Handle warehouse routing logic
        """
        logger.info(f"🏭 Notifying warehouse of order {event.order_id}")
        # TODO: Integrate with warehouse system

    async def _send_payment_receipt(self, event: OrderPaid) -> None:
        """Send payment receipt email (simulated)."""
        logger.info(
            f"💳 Sending payment receipt for order {event.order_id} (${event.total_amount})"
        )
        # TODO: Integrate with email service

    async def _initiate_fulfillment(self, event: OrderPaid) -> None:
        """Initiate order fulfillment (simulated).

        In production, this would:
        - Call fulfillment service
        - Create shipping labels
        - Assign to warehouse/carrier
        """
        logger.info(f"📤 Initiating fulfillment for order {event.order_id}")
        # TODO: Integrate with fulfillment service

    async def _update_payment_analytics(self, event: OrderPaid) -> None:
        """Update payment analytics (simulated).

        In production, this would:
        - Send to analytics platform
        - Update business metrics
        - Trigger revenue recognition
        """
        logger.info(f"📊 Updating analytics for payment: {event.order_id} (${event.total_amount})")
        # TODO: Integrate with analytics platform

    async def _send_cancellation_email(self, event: OrderCancelled) -> None:
        """Send order cancellation email (simulated)."""
        logger.info(
            f"📧 Sending cancellation email for order {event.order_id}. Reason: {event.reason}"
        )
        # TODO: Integrate with email service

    async def _release_inventory(self, event: OrderCancelled) -> None:
        """Release reserved inventory (simulated).

        In production, this would:
        - Call inventory service
        - Release reservations
        - Make stock available again
        """
        logger.info(f"📦 Releasing inventory for order {event.order_id}")
        # TODO: Integrate with inventory service

    async def _process_refund_if_needed(self, event: OrderCancelled) -> None:
        """Process refund if order was paid (simulated).

        In production, this would:
        - Check payment status
        - Call payment gateway
        - Process refund
        - Send refund confirmation
        """
        logger.info(f"💰 Processing refund check for order {event.order_id} (if applicable)")
        # TODO: Integrate with payment service
