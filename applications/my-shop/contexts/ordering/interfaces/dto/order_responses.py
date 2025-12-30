"""Order API Response Models.

These models define the structure of HTTP responses for the Order API.
They are separate from Application DTOs to allow for:
- API-specific fields (e.g., _links for HATEOAS)
- API versioning
- Field formatting and transformation
- Independent evolution from business logic
"""

from datetime import datetime

from pydantic import BaseModel, Field


class OrderItemResponse(BaseModel):
    """Order item response model for API."""

    id: str = Field(..., description="Order item ID")
    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(..., gt=0, description="Quantity")
    unit_price: float = Field(..., gt=0, description="Unit price")
    subtotal: float = Field(..., ge=0, description="Subtotal amount")


class OrderResponse(BaseModel):
    """Order response model for API."""

    id: str = Field(..., description="Order ID")
    customer_id: str = Field(..., description="Customer ID")
    status: str = Field(..., description="Order status (pending, paid, shipped, cancelled)")
    items: list[OrderItemResponse] = Field(..., description="Order items")
    total: float = Field(..., ge=0, description="Total order amount")
    created_at: datetime | None = Field(None, description="Order creation timestamp")
    paid_at: datetime | None = Field(None, description="Payment timestamp")
    shipped_at: datetime | None = Field(None, description="Shipment timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "order-123",
                "customer_id": "customer-456",
                "status": "paid",
                "items": [
                    {
                        "id": "item-789",
                        "product_id": "product-001",
                        "product_name": "Laptop",
                        "quantity": 1,
                        "unit_price": 999.99,
                        "subtotal": 999.99,
                    }
                ],
                "total": 999.99,
                "created_at": "2025-12-30T10:00:00Z",
                "paid_at": "2025-12-30T10:05:00Z",
                "shipped_at": None,
            }
        }


class ListOrdersResponse(BaseModel):
    """List orders response model for API."""

    items: list[OrderResponse] = Field(..., description="List of orders")
    total: int = Field(..., ge=0, description="Total number of orders")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "order-123",
                        "customer_id": "customer-456",
                        "status": "paid",
                        "items": [],
                        "total": 999.99,
                        "created_at": "2025-12-30T10:00:00Z",
                        "paid_at": "2025-12-30T10:05:00Z",
                        "shipped_at": None,
                    }
                ],
                "total": 1,
            }
        }
