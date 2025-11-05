from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from bento.core.clock import now_utc


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    All domain events should inherit from this class and provide
    additional fields specific to the event type.

    Attributes:
        event_id: Unique identifier for this event (for idempotency)
        name: Event type name (e.g., "OrderCreated")
        occurred_at: Timestamp when the event occurred
        tenant_id: Tenant identifier for multi-tenancy support
        aggregate_id: ID of the aggregate that produced this event
        schema_id: Schema identifier for event versioning
        schema_version: Schema version number

    Example:
        ```python
        @dataclass(frozen=True)
        class OrderCreatedEvent(DomainEvent):
            order_id: str
            customer_id: str
            total_amount: float
        ```
    """

    # Core fields - aligned with Legend implementation
    event_id: UUID = field(default_factory=uuid4)
    name: str = ""
    occurred_at: datetime = field(default_factory=now_utc)

    # Multi-tenancy support
    tenant_id: str | None = None

    # Traceability
    aggregate_id: str | None = None

    # Versioning support
    schema_id: str | None = None
    schema_version: int = 1

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage.

        Returns:
            Dictionary representation of the event
        """
        return asdict(self)
