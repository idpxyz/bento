"""Framework-level error codes for Bento framework.

This module contains ONLY framework-level error codes that are generic
and can be used across any project.

Business-specific error codes should be defined in respective modules:
    - modules/order/errors.py
    - modules/product/errors.py
    - modules/user/errors.py

Example:
    ```python
    # Framework errors (use these)
    from bento.core.error_codes import CommonErrors

    raise ApplicationException(
        error_code=CommonErrors.INVALID_PARAMS,
        details={"field": "email"}
    )

    # Business errors (define in your modules)
    # modules/order/errors.py
    class OrderErrors:
        ORDER_NOT_FOUND = ErrorCode("ORDER_001", "Order not found", 404)
    ```
"""

from bento.core.errors import ErrorCode


class CommonErrors:
    """Common framework-level error codes.

    These are generic errors that can occur in any application.
    Use these for common scenarios like validation, authorization, etc.
    """

    UNKNOWN_ERROR = ErrorCode(
        code="COMMON_000",
        message="Unknown error occurred",
        http_status=500,
    )
    """Unexpected error - should be logged and investigated"""

    INVALID_PARAMS = ErrorCode(
        code="COMMON_001",
        message="Invalid parameters",
        http_status=400,
    )
    """Request parameters validation failed"""

    RESOURCE_NOT_FOUND = ErrorCode(
        code="COMMON_002",
        message="Resource not found",
        http_status=404,
    )
    """Requested resource does not exist"""

    RESOURCE_CONFLICT = ErrorCode(
        code="COMMON_003",
        message="Resource conflict",
        http_status=409,
    )
    """Resource state conflict (e.g., duplicate, version mismatch)"""

    UNAUTHORIZED = ErrorCode(
        code="COMMON_004",
        message="Unauthorized access",
        http_status=401,
    )
    """Authentication required or failed"""

    FORBIDDEN = ErrorCode(
        code="COMMON_005",
        message="Access forbidden",
        http_status=403,
    )
    """User doesn't have permission to access resource"""

    DATABASE_ERROR = ErrorCode(
        code="COMMON_006",
        message="Database operation failed",
        http_status=500,
    )
    """Database-related error (connection, query, etc.)"""

    CACHE_ERROR = ErrorCode(
        code="COMMON_007",
        message="Cache operation failed",
        http_status=500,
    )
    """Cache-related error"""

    MESSAGING_ERROR = ErrorCode(
        code="COMMON_008",
        message="Messaging operation failed",
        http_status=500,
    )
    """Message bus/queue error"""


class RepositoryErrors:
    """Repository/persistence framework error codes.

    These errors are related to data access operations and can be
    used across different domains.
    """

    ENTITY_NOT_FOUND = ErrorCode(
        code="REPO_001",
        message="Entity not found",
        http_status=404,
    )
    """Entity doesn't exist in repository"""

    DUPLICATE_ENTITY = ErrorCode(
        code="REPO_002",
        message="Duplicate entity",
        http_status=409,
    )
    """Entity with same unique key already exists"""

    OPTIMISTIC_LOCK_FAILED = ErrorCode(
        code="REPO_003",
        message="Optimistic lock conflict",
        http_status=409,
    )
    """Entity was modified by another transaction"""

    TRANSACTION_FAILED = ErrorCode(
        code="REPO_004",
        message="Transaction failed",
        http_status=500,
    )
    """Database transaction failed"""

    QUERY_FAILED = ErrorCode(
        code="REPO_005",
        message="Query execution failed",
        http_status=500,
    )
    """Database query failed"""


# ==================== Usage Guide ====================
#
# For business-specific errors, create error codes in your modules:
#
# Example: modules/order/errors.py
# ```python
# from bento.core.errors import ErrorCode
#
# class OrderErrors:
#     """Order domain error codes."""
#
#     ORDER_NOT_FOUND = ErrorCode(
#         code="ORDER_001",
#         message="Order not found",
#         http_status=404
#     )
#
#     ORDER_ALREADY_PAID = ErrorCode(
#         code="ORDER_003",
#         message="Order is already paid",
#         http_status=409
#     )
# ```
#
# Then use in your domain:
# ```python
# from bento.core.errors import DomainException
# from modules.order.errors import OrderErrors
#
# raise DomainException(
#     error_code=OrderErrors.ORDER_NOT_FOUND,
#     details={"order_id": "123"}
# )
# ```
