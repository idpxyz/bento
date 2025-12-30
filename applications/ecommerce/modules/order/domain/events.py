"""Order domain events."""

from datetime import datetime
from uuid import UUID

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
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
        order_id: ID | str,
        customer_id: ID | str,
        total_amount: float,
        *,
        event_id: UUID | None = None,
        topic: str = "OrderCreated",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize OrderCreated event."""
        oid = order_id if isinstance(order_id, ID) else ID(order_id)
        cid = customer_id if isinstance(customer_id, ID) else ID(customer_id)

        _super_kwargs: dict[str, object] = {
            "topic": topic,
            "aggregate_id": aggregate_id or str(oid),
            "schema_version": schema_version,
        }
        if event_id is not None:
            _super_kwargs["event_id"] = event_id
        if occurred_at is not None:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id is not None:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id is not None:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)  # type: ignore[arg-type]
        object.__setattr__(self, "order_id", oid)
        object.__setattr__(self, "customer_id", cid)
        object.__setattr__(self, "total_amount", total_amount)

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage."""
        return {
            "event_id": str(self.event_id),
            "topic": self.topic,
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


@register_event
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
        order_id: ID | str,
        customer_id: ID | str,
        total_amount: float,
        paid_at: datetime | None = None,
        *,
        event_id: UUID | None = None,
        topic: str = "OrderPaid",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize OrderPaid event."""
        oid = order_id if isinstance(order_id, ID) else ID(order_id)
        cid = customer_id if isinstance(customer_id, ID) else ID(customer_id)

        _super_kwargs: dict[str, object] = {
            "topic": topic,
            "aggregate_id": aggregate_id or str(oid),
            "schema_version": schema_version,
        }
        if event_id is not None:
            _super_kwargs["event_id"] = event_id
        if occurred_at is not None:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id is not None:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id is not None:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)  # type: ignore[arg-type]
        object.__setattr__(self, "order_id", oid)
        object.__setattr__(self, "customer_id", cid)
        object.__setattr__(self, "total_amount", total_amount)
        object.__setattr__(self, "paid_at", paid_at or datetime.now())

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage."""
        return {
            "event_id": str(self.event_id),
            "topic": self.topic,
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


@register_event
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
        order_id: ID | str,
        customer_id: ID | str,
        reason: str | None = None,
        *,
        event_id: UUID | None = None,
        topic: str = "OrderCancelled",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize OrderCancelled event."""
        oid = order_id if isinstance(order_id, ID) else ID(order_id)
        cid = customer_id if isinstance(customer_id, ID) else ID(customer_id)

        _super_kwargs: dict[str, object] = {
            "topic": topic,
            "aggregate_id": aggregate_id or str(oid),
            "schema_version": schema_version,
        }
        if event_id is not None:
            _super_kwargs["event_id"] = event_id
        if occurred_at is not None:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id is not None:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id is not None:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)  # type: ignore[arg-type]
        object.__setattr__(self, "order_id", oid)
        object.__setattr__(self, "customer_id", cid)
        object.__setattr__(self, "reason", reason)

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage."""
        return {
            "event_id": str(self.event_id),
            "topic": self.topic,
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
