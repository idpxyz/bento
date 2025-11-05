"""Example: Product domain error codes.

This is an EXAMPLE of how to define domain-specific error codes.
In your real project, create this file in your business module:
    modules/product/errors.py

Usage:
    ```python
    from modules.product.errors import ProductErrors
    from core.errors import DomainException
    
    raise DomainException(
        error_code=ProductErrors.PRODUCT_NOT_FOUND,
        details={"product_id": "123"}
    )
    ```
"""

from core.errors import ErrorCode


class ProductErrors:
    """Product domain error codes.
    
    These errors are specific to the Product bounded context.
    """
    
    PRODUCT_NOT_FOUND = ErrorCode(
        code="PRODUCT_001",
        message="Product not found",
        http_status=404,
    )
    """Product with given ID doesn't exist"""
    
    INVALID_PRICE = ErrorCode(
        code="PRODUCT_002",
        message="Invalid product price",
        http_status=400,
    )
    """Product price is invalid (e.g., negative)"""
    
    OUT_OF_STOCK = ErrorCode(
        code="PRODUCT_003",
        message="Product is out of stock",
        http_status=409,
    )
    """Product stock is zero"""
    
    INVALID_QUANTITY = ErrorCode(
        code="PRODUCT_004",
        message="Invalid quantity",
        http_status=400,
    )
    """Quantity must be positive"""
    
    PRODUCT_ALREADY_EXISTS = ErrorCode(
        code="PRODUCT_005",
        message="Product already exists",
        http_status=409,
    )
    """Product with same SKU/identifier already exists"""
    
    PRODUCT_INACTIVE = ErrorCode(
        code="PRODUCT_006",
        message="Product is inactive",
        http_status=409,
    )
    """Cannot operate on inactive product"""

