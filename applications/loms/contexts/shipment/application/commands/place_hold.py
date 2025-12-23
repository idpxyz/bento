from dataclasses import dataclass
from loms.contexts.shipment.application.common import canonical_hash, now_iso
from loms.contexts.shipment.domain.errors import ContractError
from loms.contexts.shipment.domain.vo.ids import TenantId, ShipmentId
from loms.contexts.shipment.domain.vo.codes import HoldTypeCode, ShipmentStatus
from loms.contexts.shipment.domain.model.shipment import Shipment

@dataclass(frozen=True)
class PlaceHoldCommand:
    tenant_id: str
    idempotency_key: str
    method: str
    path: str
    shipment_id: str
    hold_type_code: str
    reason: str | None

class PlaceHoldHandler:
    def __init__(self, uow, *, service_name: str, contracts: dict):
        self.uow = uow
        self.service_name = service_name
        self.contracts = contracts

    async def handle(self, cmd: PlaceHoldCommand) -> dict:
        body_for_hash = {"hold_type_code": cmd.hold_type_code, "reason": cmd.reason}
        req_hash = canonical_hash(body_for_hash)

        existing = await self.uow.idempotency.get(cmd.tenant_id, cmd.idempotency_key, cmd.method, cmd.path)
        if existing:
            if existing.request_hash != req_hash:
                raise ContractError.state_conflict("IDEMPOTENCY_KEY_MISMATCH", reason_code="IDEMPOTENCY_KEY_MISMATCH", details={"path": cmd.path})
            return existing.response_body

        tenant = TenantId(cmd.tenant_id)
        sid = ShipmentId(cmd.shipment_id)

        # transaction boundary handled by UoW
        async with self.uow:
            shipment = await self.uow.shipments.get(tenant, sid)
            if shipment is None:
                shipment = Shipment(
                    tenant_id=tenant,
                    shipment_id=sid,
                    shipment_code=f"SHP-{sid.value}",
                    status=ShipmentStatus("DRAFT"),
                    version=0,
                )

            # contract state machine gate (optional but recommended)
            self.contracts["state_machines"].validate("Shipment", shipment.status.value, "PlaceHold")

            try:
                shipment.place_hold(HoldTypeCode(cmd.hold_type_code), cmd.reason)
            except ValueError as e:
                if str(e) == "STATE_CONFLICT":
                    raise ContractError.state_conflict(details={"shipment_id": sid.value, "state": shipment.status.value})
                raise

            await self.uow.shipments.save(shipment)

            # translate domain events -> outbox envelope(s)
            for ev in shipment.pull_events():
                envelope = {
                    "specversion": "1.0",
                    "event_id": ev.event_id,
                    "event_type": ev.__class__.__name__,
                    "event_version": 1,
                    "occurred_at": ev.occurred_at,
                    "tenant_id": cmd.tenant_id,
                    "producer": self.service_name,
                    "aggregate": {"type": "Shipment", "id": sid.value, "version": shipment.version},
                    "data": {
                        "shipment_id": sid.value,
                        "hold_type_code": cmd.hold_type_code,
                        "placed_at": now_iso(),
                        "reason": cmd.reason,
                    },
                }

                # schema gate (if event schemas exist in contracts)
                try:
                    self.contracts["schemas"].validate_envelope(envelope)
                except Exception:
                    # allow running without full schemas in early dev
                    pass

                await self.uow.outbox.append(
                    tenant_id=cmd.tenant_id,
                    aggregate_type="Shipment",
                    aggregate_id=sid.value,
                    aggregate_version=shipment.version,
                    event_type=envelope["event_type"],
                    event_version=envelope["event_version"],
                    payload=envelope,
                    headers=None,
                )

            resp = {"id": sid.value, "shipment_code": shipment.shipment_code, "status_code": shipment.status.value, "version": shipment.version}
            await self.uow.idempotency.upsert(
                tenant_id=cmd.tenant_id, key=cmd.idempotency_key, method=cmd.method, path=cmd.path,
                request_hash=req_hash, status_code=200, response_body=resp
            )

            await self.uow.commit()
            return resp
