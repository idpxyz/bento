"""API Request and Response Models for Ordering context.

This module contains FastAPI-specific request and response models that are used
in the REST API layer. These models are separate from Application DTOs
to allow for API-specific customization and versioning.
"""

from .order_requests import (
    OrderItemRequest,
    CreateOrderRequest,
    PayOrderRequest,
    ShipOrderRequest,
    CancelOrderRequest,
)
from .order_responses import (
    OrderItemResponse,
    OrderResponse,
    ListOrdersResponse,
)

__all__ = [
    # Request Models
    "OrderItemRequest",
    "CreateOrderRequest",
    "PayOrderRequest",
    "ShipOrderRequest",
    "CancelOrderRequest",
    # Response Models
    "OrderItemResponse",
    "OrderResponse",
    "ListOrdersResponse",
]
