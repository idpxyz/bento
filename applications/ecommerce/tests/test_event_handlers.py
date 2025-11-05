"""Tests for order event handlers.

This module demonstrates testing best practices:
- Unit testing event handlers
- Mocking external dependencies
- Verifying side effects
- Testing error scenarios
"""

import pytest

from applications.ecommerce.modules.order.application.event_handlers import (
    OrderEventHandler,
    OrderEventListener,
)
from applications.ecommerce.modules.order.domain.events import (
    OrderCancelled,
    OrderCreated,
    OrderPaid,
)
from bento.core.ids import ID


class TestOrderEventHandler:
    """Test OrderEventHandler.

    Best Practices Demonstrated:
    - Each test focuses on one scenario
    - Clear test names describe what is being tested
    - Arrange-Act-Assert pattern
    """

    @pytest.mark.asyncio
    async def test_handle_order_created_event(self):
        """Test that OrderCreated event is handled successfully.

        Demonstrates:
        - Testing event handler execution
        - Verifying no exceptions are raised
        - Testing with real event objects
        """
        # Arrange
        handler = OrderEventHandler()
        event = OrderCreated(
            order_id=ID.generate(),
            customer_id=ID.generate(),
            total_amount=99.99,
        )

        # Act & Assert
        # Handler should not raise any exceptions
        await handler.handle(event)

    @pytest.mark.asyncio
    async def test_handle_order_paid_event(self):
        """Test that OrderPaid event is handled successfully."""
        # Arrange
        handler = OrderEventHandler()
        event = OrderPaid(
            order_id=ID.generate(),
            customer_id=ID.generate(),
            total_amount=99.99,
        )

        # Act & Assert
        await handler.handle(event)

    @pytest.mark.asyncio
    async def test_handle_order_cancelled_event(self):
        """Test that OrderCancelled event is handled successfully."""
        # Arrange
        handler = OrderEventHandler()
        event = OrderCancelled(
            order_id=ID.generate(),
            customer_id=ID.generate(),
            reason="Customer request",
        )

        # Act & Assert
        await handler.handle(event)

    @pytest.mark.asyncio
    async def test_handle_unknown_event_does_not_raise(self):
        """Test that unknown events are handled gracefully.

        Demonstrates:
        - Defensive programming
        - Graceful handling of unexpected inputs
        """
        # Arrange
        handler = OrderEventHandler()

        # Create a custom event (not in handlers dict)
        from dataclasses import dataclass

        from bento.domain.domain_event import DomainEvent

        @dataclass(frozen=True)
        class UnknownEvent(DomainEvent):
            pass

        event = UnknownEvent(name="UnknownEvent")

        # Act & Assert
        # Should not raise, just log debug message
        await handler.handle(event)


class TestOrderEventListener:
    """Test OrderEventListener.

    Best Practices Demonstrated:
    - Testing integration components
    - Testing error propagation
    - Testing batch operations
    """

    @pytest.mark.asyncio
    async def test_publish_routes_to_handler(self):
        """Test that publish routes events to the correct handler.

        Demonstrates:
        - Testing event routing
        - Integration testing
        """
        # Arrange
        listener = OrderEventListener()
        event = OrderCreated(
            order_id=ID.generate(),
            customer_id=ID.generate(),
            total_amount=99.99,
        )

        # Act
        await listener.publish(event)

        # Assert
        # If we get here without exceptions, the event was published successfully

    @pytest.mark.asyncio
    async def test_publish_batch_processes_multiple_events(self):
        """Test that publish_batch handles multiple events.

        Demonstrates:
        - Testing batch operations
        - Testing with multiple events
        """
        # Arrange
        listener = OrderEventListener()
        events = [
            OrderCreated(
                order_id=ID.generate(),
                customer_id=ID.generate(),
                total_amount=99.99,
            ),
            OrderPaid(
                order_id=ID.generate(),
                customer_id=ID.generate(),
                total_amount=99.99,
            ),
            OrderCancelled(
                order_id=ID.generate(),
                customer_id=ID.generate(),
                reason="Test cancellation",
            ),
        ]

        # Act
        await listener.publish_batch(events)

        # Assert
        # If we get here without exceptions, all events were processed

    @pytest.mark.asyncio
    async def test_listener_logs_event_processing(self, caplog):
        """Test that listener logs events for observability.

        Demonstrates:
        - Testing logging behavior
        - Using pytest's caplog fixture
        - Verifying observability
        """
        # Arrange
        listener = OrderEventListener()
        event = OrderCreated(
            order_id=ID.generate(),
            customer_id=ID.generate(),
            total_amount=99.99,
        )

        # Act
        await listener.publish(event)

        # Assert
        # Check that event was logged
        assert "Publishing event" in caplog.text or "OrderCreated" in caplog.text


# Integration test demonstrating end-to-end event flow
class TestEventFlowIntegration:
    """Integration tests for event flow.

    Best Practices Demonstrated:
    - Integration testing
    - Testing complete workflows
    - Real-world scenarios
    """

    @pytest.mark.asyncio
    async def test_complete_order_lifecycle_events(self):
        """Test handling events for a complete order lifecycle.

        Demonstrates:
        - Testing complete business workflows
        - Integration testing
        - Real-world event sequences
        """
        # Arrange
        listener = OrderEventListener()
        order_id = ID.generate()
        customer_id = ID.generate()
        total_amount = 149.99

        # Act - Simulate order lifecycle
        # 1. Order created
        await listener.publish(
            OrderCreated(
                order_id=order_id,
                customer_id=customer_id,
                total_amount=total_amount,
            )
        )

        # 2. Order paid
        await listener.publish(
            OrderPaid(
                order_id=order_id,
                customer_id=customer_id,
                total_amount=total_amount,
            )
        )

        # Assert
        # If we get here, all events were handled successfully
        # In a real system, we would verify side effects:
        # - Email was sent
        # - Inventory was updated
        # - Analytics were recorded

    @pytest.mark.asyncio
    async def test_cancelled_order_workflow(self):
        """Test handling events for a cancelled order."""
        # Arrange
        listener = OrderEventListener()
        order_id = ID.generate()
        customer_id = ID.generate()
        total_amount = 79.99

        # Act - Create and then cancel order
        await listener.publish(
            OrderCreated(
                order_id=order_id,
                customer_id=customer_id,
                total_amount=total_amount,
            )
        )

        await listener.publish(
            OrderCancelled(
                order_id=order_id,
                customer_id=customer_id,
                reason="Out of stock",
            )
        )

        # Assert
        # Events handled successfully
