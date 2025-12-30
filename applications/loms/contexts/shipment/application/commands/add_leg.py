"""AddLeg command and handler."""

from dataclasses import dataclass
from datetime import datetime

from loms.contexts.shipment.domain.model import Shipment

from bento.application.cqrs.command_handler import CommandHandler
from bento.application.decorators import command_handler, idempotent, state_transition
from bento.core.exceptions import DomainException
from bento.core.ids import ID


@dataclass
class AddLegCommand:
    """Command to add a leg to a shipment."""

    tenant_id: str
    idempotency_key: str
    shipment_id: str
    leg_id: str
    origin_node_id: str
    destination_node_id: str
    planned_departure: datetime | None = None
    planned_arrival: datetime | None = None
    carrier_code: str | None = None
    mode_code: str | None = None


@command_handler
@idempotent(key_field="idempotency_key", hash_fields=["shipment_id", "leg_id"])
@state_transition(aggregate="Shipment", command="AddLeg")
class AddLegHandler(CommandHandler[AddLegCommand, dict]):
    """Handler for AddLegCommand."""

    async def handle(self, cmd: AddLegCommand) -> dict:
        """Add a leg to a shipment."""
        self.uow.set_tenant_id(cmd.tenant_id)
        shipment_repo = self.uow.repository(Shipment)

        shipment = await shipment_repo.get(ID(cmd.shipment_id))
        if shipment is None:
            raise DomainException(
                reason_code="SHIPMENT_NOT_FOUND",
                message=f"Shipment {cmd.shipment_id} not found",
                http_status=404,
            )

        shipment.add_leg(
            leg_id=ID(cmd.leg_id),
            origin_node_id=cmd.origin_node_id,
            destination_node_id=cmd.destination_node_id,
            planned_departure=cmd.planned_departure,
            planned_arrival=cmd.planned_arrival,
            carrier_code=cmd.carrier_code,
            mode_code=cmd.mode_code,
        )

        await shipment_repo.save(shipment)

        return {
            "id": str(shipment.id),
            "shipment_code": shipment.shipment_code,
            "status_code": shipment.status.value,
            "version": shipment.version,
        }
