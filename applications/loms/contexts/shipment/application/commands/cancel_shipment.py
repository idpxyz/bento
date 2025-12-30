"""CancelShipment command and handler."""
from dataclasses import dataclass

from loms.contexts.shipment.domain.model import Shipment

from bento.application.cqrs.command_handler import CommandHandler
from bento.application.decorators import command_handler, idempotent, state_transition
from bento.core.exceptions import DomainException
from bento.core.ids import ID


@dataclass
class CancelShipmentCommand:
    """Command to cancel a shipment."""

    tenant_id: str
    idempotency_key: str
    shipment_id: str
    cancel_reason: str | None = None


@command_handler
@idempotent(key_field="idempotency_key", hash_fields=["shipment_id"])
@state_transition(aggregate="Shipment", command="CancelShipment")
class CancelShipmentHandler(CommandHandler[CancelShipmentCommand, dict]):
    """Handler for CancelShipmentCommand."""

    async def handle(self, cmd: CancelShipmentCommand) -> dict:
        """Cancel a shipment."""
        self.uow.set_tenant_id(cmd.tenant_id)
        shipment_repo = self.uow.repository(Shipment)

        shipment = await shipment_repo.get(ID(cmd.shipment_id))
        if shipment is None:
            raise DomainException(
                reason_code="SHIPMENT_NOT_FOUND",
                message=f"Shipment {cmd.shipment_id} not found",
                http_status=404,
            )

        shipment.cancel(cancel_reason=cmd.cancel_reason)

        await shipment_repo.save(shipment)

        return {
            "id": str(shipment.id),
            "shipment_code": shipment.shipment_code,
            "status_code": shipment.status.value,
            "version": shipment.version,
        }
