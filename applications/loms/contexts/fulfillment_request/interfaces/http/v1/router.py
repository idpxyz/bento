from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()


class CreateFulfillmentRequest(BaseModel):
    channel_ref: str = Field(min_length=1, max_length=128)
    product_code: str = Field(min_length=1, max_length=64)
    consignee_country: str = Field(min_length=2, max_length=2, description="ISO-3166 alpha-2")
    total_weight_kg: float = Field(gt=0)


class FulfillmentRequestResponse(BaseModel):
    fr_id: str
    status: str


@router.post("/fulfillment-requests", response_model=FulfillmentRequestResponse)
async def create_fr(request: Request, body: CreateFulfillmentRequest):
    fr_id = f"FR-{body.channel_ref}"
    return FulfillmentRequestResponse(fr_id=fr_id, status="CREATED")
