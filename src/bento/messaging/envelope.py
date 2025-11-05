"""Message Envelope - Unified message format for event-driven architecture.

This module provides a standardized message wrapper that includes:
- Event metadata (type, timestamp, source)
- Tracing information (correlation_id, causation_id)
- Payload (actual event data)

All messages published to the message bus should be wrapped in MessageEnvelope
for consistent serialization, logging, and distributed tracing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from bento.core.clock import now_utc


@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    """Message envelope wrapping domain events with metadata.

    Provides a consistent structure for all messages flowing through the system,
    enabling observability, tracing, and standardized serialization.

    Attributes:
        event_type: Fully qualified event type name (e.g., "order.OrderCreated")
        payload: Event data (serializable dict)
        event_id: Unique identifier for this event instance
        occurred_at: When the event occurred (UTC)
        source: Service/module that produced the event
        correlation_id: Request trace ID (for distributed tracing)
        causation_id: ID of the event that caused this event (for event chains)
        version: Event schema version (for evolution)

    Example:
        ```python
        from bento.messaging.envelope import MessageEnvelope

        envelope = MessageEnvelope(
            event_type="order.OrderCreated",
            payload={
                "order_id": "order-123",
                "customer_id": "cust-456",
                "total": 99.99
            },
            source="order-service",
            correlation_id="req-789"
        )
        ```
    """

    event_type: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=now_utc)
    source: str = "unknown"
    correlation_id: str | None = None
    causation_id: str | None = None
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert envelope to dictionary for serialization.

        Returns:
            Dictionary representation of the envelope
        """
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageEnvelope":
        """Create envelope from dictionary (deserialization).

        Args:
            data: Dictionary containing envelope fields

        Returns:
            MessageEnvelope instance
        """
        # Parse datetime if it's a string
        occurred_at = data["occurred_at"]
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)

        return cls(
            event_type=data["event_type"],
            payload=data["payload"],
            event_id=data.get("event_id", str(uuid4())),
            occurred_at=occurred_at,
            source=data.get("source", "unknown"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            version=data.get("version", "1.0"),
        )

    def with_causation(self, event_id: str) -> "MessageEnvelope":
        """Create a new envelope with causation_id set.

        Useful for creating derivative events in event chains.

        Args:
            event_id: Event ID that caused this event

        Returns:
            New MessageEnvelope with causation_id set

        Example:
            ```python
            # Original event
            order_created = MessageEnvelope(
                event_type="order.OrderCreated",
                payload={"order_id": "123"},
                event_id="evt-001"
            )

            # Derivative event
            payment_initiated = MessageEnvelope(
                event_type="payment.PaymentInitiated",
                payload={"order_id": "123"}
            ).with_causation(order_created.event_id)
            ```
        """
        # Note: Since this is frozen dataclass, we need to create a new instance
        return MessageEnvelope(
            event_type=self.event_type,
            payload=self.payload,
            event_id=self.event_id,
            occurred_at=self.occurred_at,
            source=self.source,
            correlation_id=self.correlation_id,
            causation_id=event_id,
            version=self.version,
        )
