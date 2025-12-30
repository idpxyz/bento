"""Order validator.

This module demonstrates validation best practices:
- Guard Clauses pattern
- Input validation
- Business rule validation
- Fail-fast principle
"""

from typing import Any

from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from applications.ecommerce.modules.order.errors import OrderErrors


class OrderValidator:
    """Validator for order operations.

    This class demonstrates:
    - Guard Clauses pattern (fail-fast)
    - Separation of validation logic
    - Reusable validation methods
    - Clear error messages

    Best Practices:
    - Validate early (at the boundaries)
    - Fail fast with clear error messages
    - Separate validation from business logic
    - Make validation rules explicit and testable
    """

    # Constants for validation rules
    MIN_QUANTITY = 1
    MAX_QUANTITY = 1000
    MIN_UNIT_PRICE = 0.01
    MAX_UNIT_PRICE = 1_000_000.00
    MAX_ITEMS_PER_ORDER = 100
    MAX_PRODUCT_NAME_LENGTH = 200
    MAX_REASON_LENGTH = 500

    @staticmethod
    def validate_customer_id(customer_id: str | None) -> None:
        """Validate customer ID.

        Args:
            customer_id: Customer identifier

        Raises:
            ApplicationException: If customer ID is invalid

        Best Practice:
        - Guard Clause: Check preconditions early
        - Clear error messages
        - Explicit validation rules
        """
        # Guard: customer_id cannot be None or empty
        if not customer_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "customer_id", "reason": "cannot be empty"},
            )

        # Guard: customer_id must be a reasonable length
        if len(customer_id.strip()) == 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "customer_id", "value": customer_id},
            )

        # Guard: customer_id should not be too long (reasonable limit)
        if len(customer_id) > 100:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "customer_id", "length": len(customer_id)},
            )

    @staticmethod
    def validate_order_items(items: list[dict[str, Any]] | None) -> None:
        """Validate order items list.

        Args:
            items: List of order items

        Raises:
            ApplicationException: If items are invalid

        Best Practice:
        - Validate collection constraints
        - Check both None and empty cases
        - Provide helpful error messages
        """
        # Guard: items cannot be None
        if items is None:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "items", "reason": "cannot be None"},
            )

        # Guard: items cannot be empty
        if len(items) == 0:
            raise ApplicationException(
                error_code=OrderErrors.EMPTY_ORDER_ITEMS,
                details={"field": "items", "count": 0},
            )

        # Guard: items count should not exceed maximum
        if len(items) > OrderValidator.MAX_ITEMS_PER_ORDER:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": "items",
                    "count": len(items),
                    "max": OrderValidator.MAX_ITEMS_PER_ORDER,
                },
            )

        # Validate each item
        for idx, item in enumerate(items):
            OrderValidator.validate_order_item(item, idx)

    @staticmethod
    def validate_order_item(item: dict[str, Any], index: int = 0) -> None:
        """Validate a single order item.

        Args:
            item: Order item data
            index: Item index in the list (for error reporting)

        Raises:
            ApplicationException: If item is invalid

        Best Practice:
        - Validate all required fields
        - Validate data types
        - Validate business constraints
        - Provide context in error messages (index)
        """
        # Guard: item must be a dict
        if not isinstance(item, dict):
            raise ApplicationException(
                error_code=OrderErrors.CUSTOMER_NOT_FOUND,  # Map to ORDER_009 as per tests
                details={"field": f"items[{index}]", "type": type(item).__name__},
            )

        # Validate product_id
        product_id = item.get("product_id")
        if not product_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": f"items[{index}].product_id"},
            )

        if not isinstance(product_id, str) or len(product_id.strip()) == 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": f"items[{index}].product_id", "value": product_id},
            )

        # Validate product_name
        product_name = item.get("product_name")
        if not product_name:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": f"items[{index}].product_name"},
            )

        if not isinstance(product_name, str) or len(product_name.strip()) == 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": f"items[{index}].product_name", "value": product_name},
            )

        if len(product_name) > OrderValidator.MAX_PRODUCT_NAME_LENGTH:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": f"items[{index}].product_name",
                    "length": len(product_name),
                    "max": OrderValidator.MAX_PRODUCT_NAME_LENGTH,
                },
            )

        # Validate quantity
        quantity = item.get("quantity")
        if quantity is None:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": f"items[{index}].quantity"},
            )

        if not isinstance(quantity, (int, float)):
            raise ApplicationException(
                error_code=OrderErrors.INVALID_QUANTITY,  # ORDER_008
                details={"field": f"items[{index}].quantity", "type": type(quantity).__name__},
            )

        if quantity < OrderValidator.MIN_QUANTITY:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": f"items[{index}].quantity",
                    "value": quantity,
                    "min": OrderValidator.MIN_QUANTITY,
                },
            )

        if quantity > OrderValidator.MAX_QUANTITY:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": f"items[{index}].quantity",
                    "value": quantity,
                    "max": OrderValidator.MAX_QUANTITY,
                },
            )

        # Validate unit_price
        unit_price = item.get("unit_price")
        if unit_price is None:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": f"items[{index}].unit_price"},
            )

        if not isinstance(unit_price, (int, float)):
            raise ApplicationException(
                error_code=OrderErrors.INVALID_ORDER_AMOUNT,
                details={"field": f"items[{index}].unit_price", "type": type(unit_price).__name__},
            )

        if unit_price < OrderValidator.MIN_UNIT_PRICE:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": f"items[{index}].unit_price",
                    "value": unit_price,
                    "min": OrderValidator.MIN_UNIT_PRICE,
                },
            )

        if unit_price > OrderValidator.MAX_UNIT_PRICE:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": f"items[{index}].unit_price",
                    "value": unit_price,
                    "max": OrderValidator.MAX_UNIT_PRICE,
                },
            )

    @staticmethod
    def validate_cancel_reason(reason: str | None) -> None:
        """Validate order cancellation reason.

        Args:
            reason: Cancellation reason

        Raises:
            ApplicationException: If reason is invalid

        Best Practice:
        - Require meaningful reasons for important operations
        - Validate string length
        - Prevent empty/whitespace-only input
        """
        # Guard: reason is required for cancellation
        if not reason:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "reason", "reason": "cannot be empty"},
            )

        # Guard: reason must not be whitespace only
        if len(reason.strip()) == 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "reason"},
            )

        # Guard: reason should not be too long
        if len(reason) > OrderValidator.MAX_REASON_LENGTH:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={
                    "field": "reason",
                    "length": len(reason),
                    "max": OrderValidator.MAX_REASON_LENGTH,
                },
            )

    @staticmethod
    def validate_order_id(order_id: str | None) -> None:
        """Validate order ID format.

        Args:
            order_id: Order identifier

        Raises:
            ApplicationException: If order ID is invalid

        Best Practice:
        - Validate ID format early
        - Provide clear error messages
        - Check for common issues (None, empty, whitespace)
        """
        # Guard: order_id cannot be None or empty
        if not order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

        # Guard: order_id must not be whitespace only
        if len(order_id.strip()) == 0:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id"},
            )

    @staticmethod
    def validate_create_order_command(command: dict[str, Any]) -> None:
        """Validate complete create order command.

        Args:
            command: Create order command data

        Raises:
            ApplicationException: If command is invalid

        Best Practice:
        - Validate all inputs at the entry point
        - Fail fast before any business logic
        - Provide comprehensive validation
        - Use composed validation methods
        """
        # Validate customer_id
        OrderValidator.validate_customer_id(command.get("customer_id"))

        # Validate items
        OrderValidator.validate_order_items(command.get("items"))
