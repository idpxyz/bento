from pydantic import BaseModel, Field

class PlaceHoldRequest(BaseModel):
    hold_type_code: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=500)

class ShipmentResponse(BaseModel):
    id: str
    shipment_code: str
    status_code: str
    version: int
