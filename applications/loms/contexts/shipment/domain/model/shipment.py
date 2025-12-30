"""Shipment aggregate root - @dataclass + AggregateRoot pattern."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from loms.contexts.shipment.domain.events import (
    LegAdded,
    ShipmentClosed,
    ShipmentCreated,
    ShipmentHoldPlaced,
    ShipmentHoldReleased,
    ShipmentUpdated,
)
from loms.contexts.shipment.domain.model.hold import Hold
from loms.contexts.shipment.domain.model.leg import Leg
from loms.contexts.shipment.domain.vo.codes import (
    HoldTypeCode,
    ShipmentStatus,
    ShipmentStatusEnum,
)

from bento.core.ids import ID
from bento.domain import AggregateRoot


@dataclass
class Shipment(AggregateRoot):
    """Shipment aggregate root.

    ✅ @dataclass + AggregateRoot:
    - AutoMapper 自动检测字段
    - AggregateRoot 提供事件收集 (add_event, events, clear_events)
    - 类型安全
    """

    id: ID
    tenant_id: ID
    shipment_code: str
    status: ShipmentStatus
    mode_code: str | None = None
    service_level_code: str | None = None
    shipment_type_code: str | None = None
    legs: list[Leg] = field(default_factory=list)
    holds: list[Hold] = field(default_factory=list)
    version: int = 0

    @property
    def shipment_id(self) -> ID:
        """Alias for id."""
        return self.id

    @property
    def active_holds(self) -> list[Hold]:
        """Get active (unreleased) holds."""
        return [h for h in self.holds if h.is_active]

    @property
    def has_active_hold(self) -> bool:
        """Check if shipment has any active hold."""
        return len(self.active_holds) > 0

    # ==========================================================================
    # Command: CreateShipment (factory method)
    # ==========================================================================
    @classmethod
    def create(
        cls,
        shipment_id: ID,
        tenant_id: ID,
        shipment_code: str,
        mode_code: str | None = None,
        service_level_code: str | None = None,
        shipment_type_code: str | None = None,
    ) -> Shipment:
        """Create a new shipment in DRAFT status."""
        shipment = cls(
            id=shipment_id,
            tenant_id=tenant_id,
            shipment_code=shipment_code,
            status=ShipmentStatus(ShipmentStatusEnum.DRAFT.value),
            mode_code=mode_code,
            service_level_code=service_level_code,
            shipment_type_code=shipment_type_code,
        )
        shipment.add_event(
            ShipmentCreated(
                aggregate_id=str(shipment_id),
                tenant_id=str(tenant_id),
                shipment_id=str(shipment_id),
                shipment_code=shipment_code,
                status_code=ShipmentStatusEnum.DRAFT.value,
                mode_code=mode_code,
                service_level_code=service_level_code,
                shipment_type_code=shipment_type_code,
            )
        )
        return shipment

    # ==========================================================================
    # Command: AddLeg
    # ==========================================================================
    def add_leg(
        self,
        leg_id: ID,
        origin_node_id: str,
        destination_node_id: str,
        planned_departure: datetime | None = None,
        planned_arrival: datetime | None = None,
        carrier_code: str | None = None,
        mode_code: str | None = None,
    ) -> Leg:
        """Add a leg to the shipment."""
        if not self.status.can_add_leg:
            raise ValueError("STATE_CONFLICT: Cannot add leg in current status")

        leg_index = len(self.legs)
        leg = Leg(
            id=leg_id,
            shipment_id=self.id,
            leg_index=leg_index,
            origin_node_id=origin_node_id,
            destination_node_id=destination_node_id,
            planned_departure=planned_departure,
            planned_arrival=planned_arrival,
            carrier_code=carrier_code,
            mode_code=mode_code,
        )
        self.legs.append(leg)

        # Transition to PLANNED when first leg is added
        self.status = ShipmentStatus(ShipmentStatusEnum.PLANNED.value)

        self.add_event(
            LegAdded(
                aggregate_id=str(self.id),
                tenant_id=str(self.tenant_id),
                shipment_id=str(self.id),
                leg_id=str(leg_id),
                leg_index=leg_index,
                origin_node_id=origin_node_id,
                destination_node_id=destination_node_id,
            )
        )
        self._emit_updated()
        return leg

    # ==========================================================================
    # Command: PlaceHold
    # ==========================================================================
    def place_hold(self, hold_type: HoldTypeCode, reason: str | None, hold_id: ID | None = None) -> Hold:
        """Place a hold on the shipment."""
        if not self.status.can_place_hold:
            raise ValueError("STATE_CONFLICT: Cannot place hold in current status")

        # Check for duplicate active hold of same type
        for h in self.active_holds:
            if h.hold_type_code == hold_type.value:
                raise ValueError(f"DUPLICATE_HOLD: Active hold of type {hold_type.value} already exists")

        now = datetime.now(UTC)
        hold = Hold(
            id=hold_id or ID.generate(),
            shipment_id=self.id,
            hold_type_code=hold_type.value,
            reason=reason,
            placed_at=now,
        )
        self.holds.append(hold)
        self.status = ShipmentStatus(ShipmentStatusEnum.ON_HOLD.value)

        self.add_event(
            ShipmentHoldPlaced(
                aggregate_id=str(self.id),
                tenant_id=str(self.tenant_id),
                shipment_id=str(self.id),
                hold_type_code=hold_type.value,
                placed_at=now.isoformat(),
                reason=reason,
                shipment_version=self.version,
            )
        )
        self._emit_updated()
        return hold

    # ==========================================================================
    # Command: ReleaseHold
    # ==========================================================================
    def release_hold(self, hold_type: HoldTypeCode, release_reason: str | None = None) -> None:
        """Release a hold from the shipment."""
        if not self.status.can_release_hold:
            raise ValueError("STATE_CONFLICT: Cannot release hold in current status")

        # Find active hold of this type
        hold = next((h for h in self.active_holds if h.hold_type_code == hold_type.value), None)
        if not hold:
            raise ValueError(f"HOLD_NOT_FOUND: No active hold of type {hold_type.value}")

        now = datetime.now(UTC)
        hold.released_at = now
        hold.release_reason = release_reason

        # Transition back to PLANNED if no more active holds
        if not self.has_active_hold:
            self.status = ShipmentStatus(ShipmentStatusEnum.PLANNED.value)

        self.add_event(
            ShipmentHoldReleased(
                aggregate_id=str(self.id),
                tenant_id=str(self.tenant_id),
                shipment_id=str(self.id),
                hold_type_code=hold_type.value,
                released_at=now.isoformat(),
                release_reason=release_reason,
            )
        )
        self._emit_updated()

    # ==========================================================================
    # Command: CloseShipment
    # ==========================================================================
    def close(self, force_close_reason: str | None = None) -> None:
        """Close the shipment."""
        if not self.status.can_close:
            raise ValueError("STATE_CONFLICT: Cannot close in current status")

        if self.has_active_hold and not force_close_reason:
            raise ValueError("ACTIVE_HOLD: Cannot close with active holds without force_close_reason")

        self.status = ShipmentStatus(ShipmentStatusEnum.CLOSED.value)

        self.add_event(
            ShipmentClosed(
                aggregate_id=str(self.id),
                tenant_id=str(self.tenant_id),
                shipment_id=str(self.id),
                closed_at=datetime.now(UTC).isoformat(),
                force_close_reason=force_close_reason,
            )
        )

    # ==========================================================================
    # Command: CancelShipment
    # ==========================================================================
    def cancel(self, cancel_reason: str | None = None) -> None:
        """Cancel the shipment."""
        if not self.status.can_cancel:
            raise ValueError("STATE_CONFLICT: Cannot cancel in current status")

        self.status = ShipmentStatus(ShipmentStatusEnum.CANCELLED.value)
        self._emit_updated()

    # ==========================================================================
    # Helper
    # ==========================================================================
    def _emit_updated(self) -> None:
        """Emit ShipmentUpdated event."""
        self.add_event(
            ShipmentUpdated(
                aggregate_id=str(self.id),
                tenant_id=str(self.tenant_id),
                shipment_id=str(self.id),
                status_code=self.status.value,
                updated_at=datetime.now(UTC).isoformat(),
            )
        )

