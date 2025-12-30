"""GetShipment query handler using Bento's CQRS pattern.

Uses:
- Bento QueryHandler base class
- @query_handler decorator for DI registration
"""
from dataclasses import dataclass
from typing import Any

from loms.contexts.shipment.domain.model.shipment import Shipment

from bento.application.cqrs.query_handler import QueryHandler
from bento.application.decorators import query_handler
from bento.core.ids import ID


@dataclass(frozen=True)
class GetShipmentQuery:
    """Query to get a shipment by ID."""

    tenant_id: str
    shipment_id: str


@dataclass
class ShipmentDTO:
    """Data Transfer Object for Shipment."""

    id: str
    tenant_id: str
    shipment_code: str
    status_code: str
    mode_code: str | None
    service_level_code: str | None
    shipment_type_code: str | None
    version: int
    legs: list[dict[str, Any]]
    holds: list[dict[str, Any]]

    @classmethod
    def from_domain(cls, shipment: Shipment) -> "ShipmentDTO":
        """Create DTO from domain model."""
        return cls(
            id=shipment.shipment_id.value,
            tenant_id=shipment.tenant_id.value,
            shipment_code=shipment.shipment_code,
            status_code=shipment.status.value,
            mode_code=shipment.mode_code,
            service_level_code=shipment.service_level_code,
            shipment_type_code=shipment.shipment_type_code,
            version=shipment.version,
            legs=[
                {
                    "id": str(l.id),
                    "leg_index": l.leg_index,
                    "origin_node_id": l.origin_node_id,
                    "destination_node_id": l.destination_node_id,
                    "planned_departure": l.planned_departure,
                    "planned_arrival": l.planned_arrival,
                    "actual_departure": l.actual_departure,
                    "actual_arrival": l.actual_arrival,
                    "carrier_code": l.carrier_code,
                    "mode_code": l.mode_code,
                }
                for l in shipment.legs
            ],
            holds=[
                {
                    "id": str(h.id),
                    "hold_type_code": h.hold_type_code,
                    "reason": h.reason,
                    "placed_at": h.placed_at,
                    "released_at": h.released_at,
                    "release_reason": h.release_reason,
                    "is_active": h.is_active,
                }
                for h in shipment.holds
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "shipment_code": self.shipment_code,
            "status_code": self.status_code,
            "mode_code": self.mode_code,
            "service_level_code": self.service_level_code,
            "shipment_type_code": self.shipment_type_code,
            "version": self.version,
            "legs": self.legs,
            "holds": self.holds,
        }


@query_handler
class GetShipmentHandler(QueryHandler[GetShipmentQuery, ShipmentDTO | None]):
    """Handler for GetShipment query using Bento CQRS.

    Features:
    - Automatic DI registration via @query_handler
    - Read-only operation (no transaction commit needed)
    """

    async def handle(self, query: GetShipmentQuery) -> ShipmentDTO | None:
        """Execute GetShipment query."""
        # Set tenant for multi-tenant operations
        self.uow.set_tenant_id(query.tenant_id)

        sid = ID(query.shipment_id)

        # Get repository via Bento UoW
        shipment_repo = self.uow.repository(Shipment)
        shipment = await shipment_repo.get(sid)

        if shipment is None:
            return None

        return ShipmentDTO.from_domain(shipment)
