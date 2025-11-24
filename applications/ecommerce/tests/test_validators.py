"""Tests for order validators.

This module demonstrates testing best practices for validators:
- Testing validation rules
- Testing edge cases
- Testing error messages
- Using pytest.raises for exception testing
"""

import pytest

from applications.ecommerce.modules.order.application.validators import OrderValidator
from bento.core.errors import ApplicationException


class TestOrderValidator:
    """Test OrderValidator.

    Best Practices Demonstrated:
    - Test both valid and invalid inputs
    - Test boundary conditions
    - Test error messages and codes
    - Use descriptive test names
    """

    # Test customer_id validation

    def test_validate_customer_id_valid(self):
        """Test that valid customer ID passes validation."""
        # Should not raise
        OrderValidator.validate_customer_id("customer-123")
        OrderValidator.validate_customer_id("cust_abc123")
        OrderValidator.validate_customer_id("C" * 100)  # Max length

    def test_validate_customer_id_none_raises(self):
        """Test that None customer ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_customer_id(None)

    def test_validate_customer_id_empty_raises(self):
        """Test that empty customer ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_customer_id("")

    def test_validate_customer_id_whitespace_raises(self):
        """Test that whitespace-only customer ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_customer_id("   ")

    def test_validate_customer_id_too_long_raises(self):
        """Test that too long customer ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_customer_id("C" * 101)  # Over max

    # Test order items validation

    def test_validate_order_items_valid(self):
        """Test that valid order items pass validation."""
        valid_items = [
            {
                "product_id": "prod-1",
                "product_name": "Test Product",
                "quantity": 2,
                "unit_price": 99.99,
            }
        ]
        # Should not raise
        OrderValidator.validate_order_items(valid_items)

    def test_validate_order_items_none_raises(self):
        """Test that None items raise ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_items(None)

    def test_validate_order_items_empty_raises(self):
        """Test that empty items list raises ApplicationException."""
        with pytest.raises(ApplicationException) as exc_info:
            OrderValidator.validate_order_items([])

        assert exc_info.value.error_code.code == "ORDER_007"  # EMPTY_ORDER_ITEMS

    def test_validate_order_items_too_many_raises(self):
        """Test that too many items raise ApplicationException."""
        # Create 101 items (over MAX_ITEMS_PER_ORDER = 100)
        too_many_items = [
            {
                "product_id": f"prod-{i}",
                "product_name": f"Product {i}",
                "quantity": 1,
                "unit_price": 10.0,
            }
            for i in range(101)
        ]

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_items(too_many_items)

    # Test individual item validation

    def test_validate_order_item_missing_product_id_raises(self):
        """Test that missing product_id raises ApplicationException."""
        invalid_item = {
            "product_name": "Test",
            "quantity": 1,
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_empty_product_id_raises(self):
        """Test that empty product_id raises ApplicationException."""
        invalid_item = {
            "product_id": "",
            "product_name": "Test",
            "quantity": 1,
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_missing_product_name_raises(self):
        """Test that missing product_name raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "quantity": 1,
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_product_name_too_long_raises(self):
        """Test that too long product_name raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "P" * 201,  # Over MAX_PRODUCT_NAME_LENGTH
            "quantity": 1,
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_quantity_zero_raises(self):
        """Test that zero quantity raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": 0,
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_quantity_negative_raises(self):
        """Test that negative quantity raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": -1,
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_quantity_too_large_raises(self):
        """Test that too large quantity raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": 1001,  # Over MAX_QUANTITY
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_unit_price_zero_raises(self):
        """Test that zero unit_price raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": 1,
            "unit_price": 0.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_unit_price_negative_raises(self):
        """Test that negative unit_price raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": 1,
            "unit_price": -10.0,
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    def test_validate_order_item_unit_price_too_large_raises(self):
        """Test that too large unit_price raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": 1,
            "unit_price": 2_000_000.0,  # Over MAX_UNIT_PRICE
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_item(invalid_item)

    # Test cancel reason validation

    def test_validate_cancel_reason_valid(self):
        """Test that valid reason passes validation."""
        # Should not raise
        OrderValidator.validate_cancel_reason("Customer request")
        OrderValidator.validate_cancel_reason("Out of stock")

    def test_validate_cancel_reason_none_raises(self):
        """Test that None reason raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_cancel_reason(None)

    def test_validate_cancel_reason_empty_raises(self):
        """Test that empty reason raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_cancel_reason("")

    def test_validate_cancel_reason_whitespace_raises(self):
        """Test that whitespace-only reason raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_cancel_reason("   ")

    def test_validate_cancel_reason_too_long_raises(self):
        """Test that too long reason raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_cancel_reason("R" * 501)  # Over MAX_REASON_LENGTH

    # Test order ID validation

    def test_validate_order_id_valid(self):
        """Test that valid order ID passes validation."""
        # Should not raise
        OrderValidator.validate_order_id("order-123")
        OrderValidator.validate_order_id("550e8400-e29b-41d4-a716-446655440000")

    def test_validate_order_id_none_raises(self):
        """Test that None order ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_id(None)

    def test_validate_order_id_empty_raises(self):
        """Test that empty order ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_id("")

    def test_validate_order_id_whitespace_raises(self):
        """Test that whitespace-only order ID raises ApplicationException."""
        with pytest.raises(ApplicationException):
            OrderValidator.validate_order_id("   ")

    # Test complete command validation

    def test_validate_create_order_command_valid(self):
        """Test that valid create order command passes validation."""
        valid_command = {
            "customer_id": "customer-123",
            "items": [
                {
                    "product_id": "prod-1",
                    "product_name": "Test Product",
                    "quantity": 2,
                    "unit_price": 99.99,
                }
            ],
        }

        # Should not raise
        OrderValidator.validate_create_order_command(valid_command)

    def test_validate_create_order_command_invalid_customer_raises(self):
        """Test that invalid customer_id raises ApplicationException."""
        invalid_command = {
            "customer_id": "",  # Invalid
            "items": [
                {
                    "product_id": "prod-1",
                    "product_name": "Test Product",
                    "quantity": 2,
                    "unit_price": 99.99,
                }
            ],
        }

        with pytest.raises(ApplicationException):
            OrderValidator.validate_create_order_command(invalid_command)

    def test_validate_create_order_command_empty_items_raises(self):
        """Test that empty items raise ApplicationException."""
        invalid_command = {
            "customer_id": "customer-123",
            "items": [],  # Empty
        }

        with pytest.raises(ApplicationException) as exc_info:
            OrderValidator.validate_create_order_command(invalid_command)

        assert "at least one item" in str(exc_info.value).lower()


class TestValidatorEdgeCases:
    """Test edge cases and boundary conditions.

    Best Practices Demonstrated:
    - Testing boundary values
    - Testing special characters
    - Testing type mismatches
    """

    def test_item_with_special_characters_in_names(self):
        """Test that items with special characters are valid."""
        item = {
            "product_id": "prod-123-ABC",
            "product_name": "Product™ with émojis 🎉",
            "quantity": 1,
            "unit_price": 10.0,
        }

        # Should not raise
        OrderValidator.validate_order_item(item)

    def test_item_with_float_quantity(self):
        """Test that float quantity is accepted."""
        item = {
            "product_id": "prod-1",
            "product_name": "Fractional Product",
            "quantity": 2.5,  # Float
            "unit_price": 10.0,
        }

        # Should not raise (quantity accepts float)
        OrderValidator.validate_order_item(item)

    def test_item_with_very_precise_price(self):
        """Test that very precise prices are handled."""
        item = {
            "product_id": "prod-1",
            "product_name": "Precise Price",
            "quantity": 1,
            "unit_price": 10.999999,  # Many decimals
        }

        # Should not raise
        OrderValidator.validate_order_item(item)

    def test_item_with_wrong_type_raises(self):
        """Test that wrong item type raises ApplicationException."""
        with pytest.raises(ApplicationException) as exc_info:
            OrderValidator.validate_order_item("not a dict", 0)  # type: ignore[arg-type]
        assert exc_info.value.error_code.code == "ORDER_009"  # WRONG_ITEM_TYPE

    def test_item_with_non_numeric_quantity_raises(self):
        """Test that non-numeric quantity raises ApplicationException."""
        invalid_item = {
            "product_id": "prod-1",
            "product_name": "Test",
            "quantity": "five",  # String instead of number
            "unit_price": 10.0,
        }

        with pytest.raises(ApplicationException) as exc_info:
            OrderValidator.validate_order_item(invalid_item)
        assert exc_info.value.error_code.code == "ORDER_008"  # NON_NUMERIC_QUANTITY
