"""Shipment domain events.

Uses Bento's DomainEvent for automatic serialization and schema support.
All events follow contract schemas in contracts/loms/v1.0.0/events/shipment/
"""

from dataclasses import dataclass, field

from bento.domain import DomainEvent


@dataclass(frozen=True)
class ShipmentCreated(DomainEvent):
    """Event emitted when a shipment is created.

    Schema: contracts/loms/v1.0.0/events/shipment/ShipmentCreated.v1.schema.json
    """

    shipment_id: str = field(default="")
    shipment_code: str = field(default="")
    status_code: str = field(default="")
    mode_code: str | None = field(default=None)
    service_level_code: str | None = field(default=None)
    shipment_type_code: str | None = field(default=None)


@dataclass(frozen=True)
class ShipmentUpdated(DomainEvent):
    """Event emitted when a shipment is updated.

    Schema: contracts/loms/v1.0.0/events/shipment/ShipmentUpdated.v1.schema.json
    """

    shipment_id: str = field(default="")
    status_code: str = field(default="")
    updated_at: str = field(default="")  # ISO 8601 datetime


@dataclass(frozen=True)
class ShipmentHoldPlaced(DomainEvent):
    """Event emitted when a hold is placed on a shipment.

    Schema: contracts/loms/v1.0.0/events/shipment/ShipmentHoldPlaced.v1.schema.json
    """

    shipment_id: str = field(default="")
    hold_type_code: str = field(default="")
    placed_at: str = field(default="")  # ISO 8601 datetime
    reason: str | None = field(default=None)
    shipment_version: int = field(default=0)


@dataclass(frozen=True)
class ShipmentHoldReleased(DomainEvent):
    """Event emitted when a hold is released from a shipment.

    Schema: contracts/loms/v1.0.0/events/shipment/ShipmentHoldReleased.v1.schema.json
    """

    shipment_id: str = field(default="")
    hold_type_code: str = field(default="")
    released_at: str = field(default="")  # ISO 8601 datetime
    release_reason: str | None = field(default=None)


@dataclass(frozen=True)
class ShipmentClosed(DomainEvent):
    """Event emitted when a shipment is closed.

    Schema: contracts/loms/v1.0.0/events/shipment/ShipmentClosed.v1.schema.json
    """

    shipment_id: str = field(default="")
    closed_at: str = field(default="")  # ISO 8601 datetime
    force_close_reason: str | None = field(default=None)


@dataclass(frozen=True)
class LegAdded(DomainEvent):
    """Event emitted when a leg is added to a shipment."""

    shipment_id: str = field(default="")
    leg_id: str = field(default="")
    leg_index: int = field(default=0)
    origin_node_id: str = field(default="")
    destination_node_id: str = field(default="")
