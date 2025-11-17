"""Order API Schemas (DTOs)"""

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    """Schema for creating an order item"""

    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity")
    unit_price: float = Field(..., gt=0, description="Unit price")


class OrderItemResponse(BaseModel):
    """Schema for order item response"""

    id: str
    product_id: str
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    """Schema for creating an order"""

    customer_id: str = Field(..., description="Customer ID")
    items: list[OrderItemCreate] = Field(..., min_length=1, description="Order items")


class OrderResponse(BaseModel):
    """Schema for order response"""

    id: str
    customer_id: str
    status: str
    total_amount: float
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderList(BaseModel):
    """Schema for order list response"""

    items: list[OrderResponse]
    total: int
    page: int
    page_size: int


class OrderActionResponse(BaseModel):
    """Schema for order action response"""

    order_id: str
    status: str
    message: str
