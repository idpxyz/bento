from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Request DTOs
# =============================================================================


class CreateShipmentRequest(BaseModel):
    """Request to create a new shipment."""
    shipment_code: str = Field(min_length=1, max_length=64)
    mode_code: str | None = Field(default=None, max_length=32)
    service_level_code: str | None = Field(default=None, max_length=32)
    shipment_type_code: str | None = Field(default=None, max_length=32)


class AddLegRequest(BaseModel):
    """Request to add a leg to a shipment."""
    leg_id: str = Field(min_length=1, max_length=64)
    origin_node_id: str = Field(min_length=1, max_length=64)
    destination_node_id: str = Field(min_length=1, max_length=64)
    planned_departure: datetime | None = None
    planned_arrival: datetime | None = None
    carrier_code: str | None = Field(default=None, max_length=32)
    mode_code: str | None = Field(default=None, max_length=32)


class PlaceHoldRequest(BaseModel):
    """Request to place a hold on a shipment."""
    hold_type_code: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=500)


class ReleaseHoldRequest(BaseModel):
    """Request to release a hold from a shipment."""
    hold_type_code: str = Field(min_length=1, max_length=64)
    release_reason: str | None = Field(default=None, max_length=500)


class CloseShipmentRequest(BaseModel):
    """Request to close a shipment."""
    force_close_reason: str | None = Field(default=None, max_length=500)


class CancelShipmentRequest(BaseModel):
    """Request to cancel a shipment."""
    cancel_reason: str | None = Field(default=None, max_length=500)


# =============================================================================
# Response DTOs
# =============================================================================


class LegResponse(BaseModel):
    """Leg response."""
    id: str
    leg_index: int
    origin_node_id: str
    destination_node_id: str
    planned_departure: datetime | None = None
    planned_arrival: datetime | None = None
    actual_departure: datetime | None = None
    actual_arrival: datetime | None = None
    carrier_code: str | None = None
    mode_code: str | None = None


class HoldResponse(BaseModel):
    """Hold response."""
    id: str
    hold_type_code: str
    reason: str | None = None
    placed_at: datetime
    released_at: datetime | None = None
    release_reason: str | None = None
    is_active: bool


class ShipmentResponse(BaseModel):
    """Shipment response."""
    id: str
    shipment_code: str
    status_code: str
    mode_code: str | None = None
    service_level_code: str | None = None
    shipment_type_code: str | None = None
    version: int


class ShipmentDetailResponse(ShipmentResponse):
    """Detailed shipment response with legs and holds."""
    legs: list[LegResponse] = []
    holds: list[HoldResponse] = []
