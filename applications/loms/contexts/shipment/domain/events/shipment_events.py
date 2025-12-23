from dataclasses import dataclass
from loms.contexts.shipment.domain.events.base import DomainEvent

@dataclass(frozen=True)
class ShipmentHoldPlaced(DomainEvent):
    shipment_id: str
    hold_type_code: str
    reason: str | None
    shipment_version: int
