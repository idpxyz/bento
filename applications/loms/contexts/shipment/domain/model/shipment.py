from dataclasses import dataclass, field
from loms.contexts.shipment.domain.vo.ids import TenantId, ShipmentId
from loms.contexts.shipment.domain.vo.codes import ShipmentStatus, HoldTypeCode
from loms.contexts.shipment.domain.events.shipment_events import ShipmentHoldPlaced
from loms.contexts.shipment.domain.events.base import DomainEvent

@dataclass
class Shipment:
    tenant_id: TenantId
    shipment_id: ShipmentId
    shipment_code: str
    status: ShipmentStatus
    version: int = 0
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    def place_hold(self, hold_type: HoldTypeCode, reason: str | None):
        # Example invariant / state rule (should be driven by contract state machine externally too)
        if self.status.value in {"CANCELLED", "DELIVERED"}:
            raise ValueError("STATE_CONFLICT")
        self.status = ShipmentStatus("ON_HOLD")
        self.version += 1
        self._events.append(ShipmentHoldPlaced(
            event_id=DomainEvent.new_id(),
            occurred_at=DomainEvent.now(),
            shipment_id=self.shipment_id.value,
            hold_type_code=hold_type.value,
            reason=reason,
            shipment_version=self.version,
        ))

    def pull_events(self) -> list[DomainEvent]:
        ev = list(self._events)
        self._events.clear()
        return ev
