"""Order domain events."""

from datetime import datetime

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent


class OrderCreated(DomainEvent):
    """Order created event.

    Published when a new order is created.

    Attributes:
        order_id: The ID of the created order
        customer_id: The ID of the customer who placed the order
        total_amount: Total amount of the order
    """

    order_id: ID
    customer_id: ID
    total_amount: float

    def __init__(
        self,
        order_id: ID,
        customer_id: ID,
        total_amount: float,
    ) -> None:
        """Initialize OrderCreated event."""
        super().__init__(
            name="OrderCreated",
            aggregate_id=str(order_id),  # ← 设置 aggregate_id
        )
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "total_amount", total_amount)

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage."""
        return {
            "event_id": str(self.event_id),
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": self.tenant_id,
            "aggregate_id": self.aggregate_id,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            # Business fields
            "order_id": str(self.order_id),
            "customer_id": str(self.customer_id),
            "total_amount": self.total_amount,
        }


class OrderPaid(DomainEvent):
    """Order paid event.

    Published when an order is successfully paid.

    Attributes:
        order_id: The ID of the paid order
        customer_id: The ID of the customer
        total_amount: Total amount paid
        paid_at: Timestamp when the payment was completed
    """

    order_id: ID
    customer_id: ID
    total_amount: float
    paid_at: datetime

    def __init__(
        self,
        order_id: ID,
        customer_id: ID,
        total_amount: float,
        paid_at: datetime | None = None,
    ) -> None:
        """Initialize OrderPaid event."""
        super().__init__(
            name="OrderPaid",
            aggregate_id=str(order_id),  # ← 设置 aggregate_id
        )
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "total_amount", total_amount)
        object.__setattr__(self, "paid_at", paid_at or datetime.now())

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage."""
        return {
            "event_id": str(self.event_id),
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": self.tenant_id,
            "aggregate_id": self.aggregate_id,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            # Business fields
            "order_id": str(self.order_id),
            "customer_id": str(self.customer_id),
            "total_amount": self.total_amount,
            "paid_at": self.paid_at.isoformat(),
        }


class OrderCancelled(DomainEvent):
    """Order cancelled event.

    Published when an order is cancelled.

    Attributes:
        order_id: The ID of the cancelled order
        customer_id: The ID of the customer
        reason: Optional reason for cancellation
    """

    order_id: ID
    customer_id: ID
    reason: str | None

    def __init__(
        self,
        order_id: ID,
        customer_id: ID,
        reason: str | None = None,
    ) -> None:
        """Initialize OrderCancelled event."""
        super().__init__(
            name="OrderCancelled",
            aggregate_id=str(order_id),  # ← 设置 aggregate_id
        )
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "reason", reason)

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage."""
        return {
            "event_id": str(self.event_id),
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": self.tenant_id,
            "aggregate_id": self.aggregate_id,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            # Business fields
            "order_id": str(self.order_id),
            "customer_id": str(self.customer_id),
            "reason": self.reason,
        }
