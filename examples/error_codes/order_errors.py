"""Example: Order domain error codes.

This is an EXAMPLE of how to define domain-specific error codes.
In your real project, create this file in your business module:
    modules/order/errors.py

Usage:
    ```python
    from modules.order.errors import OrderErrors
    from core.errors import DomainException
    
    raise DomainException(
        error_code=OrderErrors.ORDER_NOT_FOUND,
        details={"order_id": "123"}
    )
    ```
"""

from core.errors import ErrorCode


class OrderErrors:
    """Order domain error codes.
    
    These errors are specific to the Order bounded context.
    """
    
    ORDER_NOT_FOUND = ErrorCode(
        code="ORDER_001",
        message="Order not found",
        http_status=404,
    )
    """Order with given ID doesn't exist"""
    
    INVALID_ORDER_STATUS = ErrorCode(
        code="ORDER_002",
        message="Invalid order status",
        http_status=400,
    )
    """Order status transition is not allowed"""
    
    ORDER_ALREADY_PAID = ErrorCode(
        code="ORDER_003",
        message="Order is already paid",
        http_status=409,
    )
    """Cannot modify paid order"""
    
    ORDER_ALREADY_CANCELLED = ErrorCode(
        code="ORDER_004",
        message="Order is already cancelled",
        http_status=409,
    )
    """Cannot modify cancelled order"""
    
    INSUFFICIENT_STOCK = ErrorCode(
        code="ORDER_005",
        message="Insufficient product stock",
        http_status=409,
    )
    """Product stock is not enough for the order"""
    
    INVALID_ORDER_AMOUNT = ErrorCode(
        code="ORDER_006",
        message="Invalid order amount",
        http_status=400,
    )
    """Order amount is invalid (e.g., negative, zero)"""
    
    EMPTY_ORDER_ITEMS = ErrorCode(
        code="ORDER_007",
        message="Order must contain at least one item",
        http_status=400,
    )
    """Cannot create order without items"""

