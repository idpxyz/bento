"""CreateShipment command and handler."""

from dataclasses import dataclass

from loms.contexts.shipment.domain.model import Shipment

from bento.application.cqrs.command_handler import CommandHandler
from bento.application.decorators import command_handler, idempotent, state_transition
from bento.core.ids import ID


@dataclass
class CreateShipmentCommand:
    """Command to create a new shipment."""

    tenant_id: str
    idempotency_key: str
    shipment_id: str
    shipment_code: str
    mode_code: str | None = None
    service_level_code: str | None = None
    shipment_type_code: str | None = None


@command_handler
@idempotent(key_field="idempotency_key", hash_fields=["shipment_id", "shipment_code"])
@state_transition(aggregate="Shipment", command="CreateShipment")
class CreateShipmentHandler(CommandHandler[CreateShipmentCommand, dict]):
    """Handler for CreateShipmentCommand."""

    async def handle(self, cmd: CreateShipmentCommand) -> dict:
        """Create a new shipment."""
        self.uow.set_tenant_id(cmd.tenant_id)
        shipment_repo = self.uow.repository(Shipment)

        # Check if shipment already exists
        existing = await shipment_repo.get(ID(cmd.shipment_id))
        if existing:
            return {
                "id": str(existing.id),
                "shipment_code": existing.shipment_code,
                "status_code": existing.status.value,
                "version": existing.version,
            }

        # Create new shipment
        shipment = Shipment.create(
            shipment_id=ID(cmd.shipment_id),
            tenant_id=ID(cmd.tenant_id),
            shipment_code=cmd.shipment_code,
            mode_code=cmd.mode_code,
            service_level_code=cmd.service_level_code,
            shipment_type_code=cmd.shipment_type_code,
        )

        await shipment_repo.save(shipment)

        return {
            "id": str(shipment.id),
            "shipment_code": shipment.shipment_code,
            "status_code": shipment.status.value,
            "mode_code": shipment.mode_code,
            "service_level_code": shipment.service_level_code,
            "shipment_type_code": shipment.shipment_type_code,
            "version": shipment.version,
        }
