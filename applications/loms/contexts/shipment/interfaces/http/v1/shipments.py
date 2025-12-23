from fastapi import APIRouter, Request, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loms.contexts.shipment.interfaces.http.v1.dtos import PlaceHoldRequest, ShipmentResponse
from loms.shared.infra.db.session import get_session
from loms.contexts.shipment.infra.persistence.uow import SqlAlchemyUnitOfWork
from loms.contexts.shipment.application.commands.place_hold import PlaceHoldHandler, PlaceHoldCommand

router = APIRouter()

@router.post("/shipments/{shipment_id}/holds", response_model=ShipmentResponse)
async def place_hold(
    shipment_id: str,
    request: Request,
    body: PlaceHoldRequest,
    session: AsyncSession = Depends(get_session),
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    tenant_id = x_tenant_id
    idem_key = x_idempotency_key
    method = request.method
    path = request.url.path

    uow = SqlAlchemyUnitOfWork(session)
    handler = PlaceHoldHandler(uow=uow, service_name=request.app.state.service_name, contracts=request.app.state.contracts)

    resp = await handler.handle(PlaceHoldCommand(
        tenant_id=tenant_id,
        idempotency_key=idem_key,
        method=method,
        path=path,
        shipment_id=shipment_id,
        hold_type_code=body.hold_type_code,
        reason=body.reason,
    ))
    return resp
