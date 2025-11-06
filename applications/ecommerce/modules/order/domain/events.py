"""Order domain events."""

from datetime import datetime
from typing import Any

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent


class OrderCreated(DomainEvent):
    """Order created event.

    Published when a new order is created.
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
        super().__init__(name="OrderCreated")
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "total_amount", total_amount)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": "OrderCreated",
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": str(self.order_id),
            "customer_id": str(self.customer_id),
            "total_amount": self.total_amount,
        }


class OrderPaid(DomainEvent):
    """Order paid event.

    Published when an order is successfully paid.
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
        super().__init__(name="OrderPaid")
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "total_amount", total_amount)
        object.__setattr__(self, "paid_at", paid_at or datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": "OrderPaid",
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": str(self.order_id),
            "customer_id": str(self.customer_id),
            "total_amount": self.total_amount,
            "paid_at": self.paid_at.isoformat(),
        }


class OrderCancelled(DomainEvent):
    """Order cancelled event.

    Published when an order is cancelled.
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
        super().__init__(name="OrderCancelled")
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "reason", reason)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": "OrderCancelled",
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": str(self.order_id),
            "customer_id": str(self.customer_id),
            "reason": self.reason,
        }
