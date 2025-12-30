"""Shipment Mapper using Bento's AutoMapper."""
from bento.application.mappers import AutoMapper
from bento.core.ids import ID

from loms.contexts.shipment.domain.model import Shipment, Leg, Hold
from loms.contexts.shipment.domain.vo.codes import ShipmentStatus
from loms.contexts.shipment.infra.persistence.models import ShipmentORM, LegORM, HoldORM


class ShipmentMapper(AutoMapper[Shipment, ShipmentORM]):
    """Mapper for Shipment AR <-> ShipmentORM PO."""

    def __init__(self) -> None:
        super().__init__(Shipment, ShipmentORM)

        # Field name mapping: domain -> PO
        self.alias_field("status", "status_code")

        # Ignore internal fields
        self.ignore_fields("_events")

        # Custom type converters for reverse mapping (PO -> AR)
        self.override_field(
            "status",
            to_po=lambda v: v.value if hasattr(v, "value") else v,
            from_po=lambda v: ShipmentStatus(v) if isinstance(v, str) else v,
        )
        self.override_field(
            "id",
            to_po=lambda v: str(v) if v else v,
            from_po=lambda v: ID(v) if isinstance(v, str) else v,
        )
        self.override_field(
            "tenant_id",
            to_po=lambda v: str(v) if v else v,
            from_po=lambda v: ID(v) if isinstance(v, str) else v,
        )

        # Nested legs / holds
        self.override_field(
            "legs",
            to_po=lambda legs: [self._map_leg_to_po(l) for l in (legs or [])],
            from_po=lambda legs: [self._map_leg_from_po(l) for l in (legs or [])],
        )
        self.override_field(
            "holds",
            to_po=lambda holds: [self._map_hold_to_po(h) for h in (holds or [])],
            from_po=lambda holds: [self._map_hold_from_po(h) for h in (holds or [])],
        )

        # Rebuild mappings to apply overrides
        self.rebuild_mappings()

    # ------------------------------------------------------------------
    # Helpers for nested mapping (Leg / Hold)
    # ------------------------------------------------------------------
    @staticmethod
    def _map_leg_to_po(leg: Leg) -> LegORM:
        return LegORM(
            id=str(leg.id),
            shipment_id=str(leg.shipment_id),
            leg_index=leg.leg_index,
            origin_node_id=leg.origin_node_id,
            destination_node_id=leg.destination_node_id,
            planned_departure=leg.planned_departure,
            planned_arrival=leg.planned_arrival,
            actual_departure=leg.actual_departure,
            actual_arrival=leg.actual_arrival,
            carrier_code=leg.carrier_code,
            mode_code=leg.mode_code,
        )

    @staticmethod
    def _map_leg_from_po(po: LegORM) -> Leg:
        return Leg(
            id=ID(po.id),
            shipment_id=ID(po.shipment_id),
            leg_index=po.leg_index,
            origin_node_id=po.origin_node_id,
            destination_node_id=po.destination_node_id,
            planned_departure=po.planned_departure,
            planned_arrival=po.planned_arrival,
            actual_departure=po.actual_departure,
            actual_arrival=po.actual_arrival,
            carrier_code=po.carrier_code,
            mode_code=po.mode_code,
        )

    @staticmethod
    def _map_hold_to_po(hold: Hold) -> HoldORM:
        return HoldORM(
            id=str(hold.id),
            shipment_id=str(hold.shipment_id),
            hold_type_code=hold.hold_type_code,
            reason=hold.reason,
            placed_at=hold.placed_at,
            released_at=hold.released_at,
            release_reason=hold.release_reason,
        )

    @staticmethod
    def _map_hold_from_po(po: HoldORM) -> Hold:
        return Hold(
            id=ID(po.id),
            shipment_id=ID(po.shipment_id),
            hold_type_code=po.hold_type_code,
            reason=po.reason,
            placed_at=po.placed_at,
            released_at=po.released_at,
            release_reason=po.release_reason,
        )
