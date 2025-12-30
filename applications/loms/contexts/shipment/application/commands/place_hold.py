"""PlaceHold command handler using Bento's CQRS pattern.

Uses:
- Bento CommandHandler base class
- @idempotent decorator for automatic idempotency handling
- @state_transition decorator for Contract-as-Code validation
- @command_handler decorator for DI registration
"""
from dataclasses import dataclass

from loms.contexts.shipment.domain.model.shipment import Shipment
from loms.contexts.shipment.domain.vo.codes import HoldTypeCode, ShipmentStatus

from bento.application.cqrs.command_handler import CommandHandler
from bento.application.decorators import command_handler, idempotent, state_transition
from bento.core.exceptions import DomainException
from bento.core.ids import ID


@dataclass(frozen=True)
class PlaceHoldCommand:
    """Command to place a hold on a shipment."""

    tenant_id: str
    idempotency_key: str
    shipment_id: str
    hold_type_code: str
    reason: str | None


@idempotent(key_field="idempotency_key", hash_fields=["hold_type_code", "reason"])
@state_transition(aggregate="Shipment", command="PlaceHold", state_field="status")
@command_handler
class PlaceHoldHandler(CommandHandler[PlaceHoldCommand, dict]):
    """Handler for PlaceHold command using Bento CQRS.

    Features:
    - Automatic idempotency via @idempotent
    - Automatic state machine validation via @state_transition
    - Automatic DI registration via @command_handler
    - Event tracking and outbox
    """

    async def handle(self, cmd: PlaceHoldCommand) -> dict:
        """Execute PlaceHold command - only business logic here."""
        # Set tenant for multi-tenant operations
        self.uow.set_tenant_id(cmd.tenant_id)

        # Set TenantContext for repository filtering
        from bento.multitenancy import TenantContext
        TenantContext.set(cmd.tenant_id)

        tenant = ID(cmd.tenant_id)
        sid = ID(cmd.shipment_id)

        # Get repository via Bento UoW
        shipment_repo = self.uow.repository(Shipment)
        shipment = await shipment_repo.get(sid)

        if shipment is None:
            shipment = Shipment(
                id=sid,
                tenant_id=tenant,
                shipment_code=f"SHP-{sid}",
                status=ShipmentStatus("DRAFT"),
                version=0,
            )

        # Execute domain logic
        try:
            shipment.place_hold(HoldTypeCode(cmd.hold_type_code), cmd.reason)
        except ValueError as e:
            if str(e) == "STATE_CONFLICT":
                raise DomainException(
                    reason_code="STATE_CONFLICT",
                    message="State conflict",
                    http_status=409,
                    details={"shipment_id": str(sid), "state": shipment.status.value},
                )
            raise

        await shipment_repo.save(shipment)

        # Track aggregate for event collection
        self.uow.track(shipment)

        # Build and return response (idempotency handled by decorator)
        return {
            "id": str(sid),
            "shipment_code": shipment.shipment_code,
            "status_code": shipment.status.value,
            "version": shipment.version,
        }
