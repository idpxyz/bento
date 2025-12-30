"""Shipment HTTP endpoints using Bento CQRS + DI pattern.

Uses:
- handler_dependency for automatic handler injection
- Bento's CommandHandler and QueryHandler patterns
"""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from loms.contexts.shipment.application.commands import (
    AddLegCommand,
    AddLegHandler,
    CancelShipmentCommand,
    CancelShipmentHandler,
    CloseShipmentCommand,
    CloseShipmentHandler,
    CreateShipmentCommand,
    CreateShipmentHandler,
    PlaceHoldCommand,
    PlaceHoldHandler,
    ReleaseHoldCommand,
    ReleaseHoldHandler,
)
from loms.contexts.shipment.application.queries.get_shipment import (
    GetShipmentHandler,
    GetShipmentQuery,
)
from loms.contexts.shipment.interfaces.http.v1.dtos import (
    AddLegRequest,
    CancelShipmentRequest,
    CloseShipmentRequest,
    CreateShipmentRequest,
    PlaceHoldRequest,
    ReleaseHoldRequest,
    ShipmentResponse,
)

from bento.core import get_exception_responses_schema
from bento.interfaces.fastapi import handler_dependency

router = APIRouter()

# Common error responses for API documentation
ERROR_RESPONSES = get_exception_responses_schema()


# =============================================================================
# CreateShipment
# =============================================================================
@router.post(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Create a shipment",
    description="Creates a new shipment in DRAFT status.",
)
async def create_shipment(
    shipment_id: str,
    body: CreateShipmentRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
    handler: Annotated[CreateShipmentHandler, handler_dependency(CreateShipmentHandler)],
):
    """Create a new shipment."""
    return await handler.execute(
        CreateShipmentCommand(
            tenant_id=x_tenant_id,
            idempotency_key=x_idempotency_key,
            shipment_id=shipment_id,
            shipment_code=body.shipment_code,
            mode_code=body.mode_code,
            service_level_code=body.service_level_code,
            shipment_type_code=body.shipment_type_code,
        )
    )


# =============================================================================
# GetShipment
# =============================================================================
@router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Get a shipment by ID",
    description="Retrieves a shipment by its ID for the current tenant.",
)
async def get_shipment(
    shipment_id: str,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    handler: Annotated[GetShipmentHandler, handler_dependency(GetShipmentHandler)],
):
    """Get a shipment by ID."""
    result = await handler.execute(
        GetShipmentQuery(
            tenant_id=x_tenant_id,
            shipment_id=shipment_id,
        )
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return result.to_dict()


# =============================================================================
# AddLeg
# =============================================================================
@router.post(
    "/shipments/{shipment_id}/legs",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Add a leg to a shipment",
    description="Adds a leg to a shipment. Transitions from DRAFT to PLANNED.",
)
async def add_leg(
    shipment_id: str,
    body: AddLegRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
    handler: Annotated[AddLegHandler, handler_dependency(AddLegHandler)],
):
    """Add a leg to a shipment."""
    return await handler.execute(
        AddLegCommand(
            tenant_id=x_tenant_id,
            idempotency_key=x_idempotency_key,
            shipment_id=shipment_id,
            leg_id=body.leg_id,
            origin_node_id=body.origin_node_id,
            destination_node_id=body.destination_node_id,
            planned_departure=body.planned_departure,
            planned_arrival=body.planned_arrival,
            carrier_code=body.carrier_code,
            mode_code=body.mode_code,
        )
    )


# =============================================================================
# PlaceHold
# =============================================================================
@router.post(
    "/shipments/{shipment_id}/holds",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Place a hold on a shipment",
    description="Places a hold on a shipment. Transitions to ON_HOLD status.",
)
async def place_hold(
    shipment_id: str,
    body: PlaceHoldRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
    handler: Annotated[PlaceHoldHandler, handler_dependency(PlaceHoldHandler)],
):
    """Place a hold on a shipment."""
    return await handler.execute(
        PlaceHoldCommand(
            tenant_id=x_tenant_id,
            idempotency_key=x_idempotency_key,
            shipment_id=shipment_id,
            hold_type_code=body.hold_type_code,
            reason=body.reason,
        )
    )


# =============================================================================
# ReleaseHold
# =============================================================================
@router.delete(
    "/shipments/{shipment_id}/holds",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Release a hold from a shipment",
    description="Releases a hold from a shipment. Returns to PLANNED if no more holds.",
)
async def release_hold(
    shipment_id: str,
    body: ReleaseHoldRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
    handler: Annotated[ReleaseHoldHandler, handler_dependency(ReleaseHoldHandler)],
):
    """Release a hold from a shipment."""
    return await handler.execute(
        ReleaseHoldCommand(
            tenant_id=x_tenant_id,
            idempotency_key=x_idempotency_key,
            shipment_id=shipment_id,
            hold_type_code=body.hold_type_code,
            release_reason=body.release_reason,
        )
    )


# =============================================================================
# CloseShipment
# =============================================================================
@router.post(
    "/shipments/{shipment_id}/close",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Close a shipment",
    description="Closes a shipment. Transitions to CLOSED status.",
)
async def close_shipment(
    shipment_id: str,
    body: CloseShipmentRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
    handler: Annotated[CloseShipmentHandler, handler_dependency(CloseShipmentHandler)],
):
    """Close a shipment."""
    return await handler.execute(
        CloseShipmentCommand(
            tenant_id=x_tenant_id,
            idempotency_key=x_idempotency_key,
            shipment_id=shipment_id,
            force_close_reason=body.force_close_reason,
        )
    )


# =============================================================================
# CancelShipment
# =============================================================================
@router.post(
    "/shipments/{shipment_id}/cancel",
    response_model=ShipmentResponse,
    responses=ERROR_RESPONSES,
    summary="Cancel a shipment",
    description="Cancels a shipment. Transitions to CANCELLED status.",
)
async def cancel_shipment(
    shipment_id: str,
    body: CancelShipmentRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
    handler: Annotated[CancelShipmentHandler, handler_dependency(CancelShipmentHandler)],
):
    """Cancel a shipment."""
    return await handler.execute(
        CancelShipmentCommand(
            tenant_id=x_tenant_id,
            idempotency_key=x_idempotency_key,
            shipment_id=shipment_id,
            cancel_reason=body.cancel_reason,
        )
    )
