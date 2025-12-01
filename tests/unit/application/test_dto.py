"""Unit tests for DTO classes."""

import json
from datetime import datetime

import pytest
from pydantic import Field, ValidationError

from bento.application.dto.base import BaseDTO, ErrorDTO, ListDTO


class ProductDTO(BaseDTO):
    """Test DTO for products."""

    id: str = Field(..., description="Product ID")
    name: str = Field(..., min_length=1, description="Product name")
    price: float = Field(..., gt=0, description="Product price")
    created_at: datetime
    internal_notes: str | None = Field(None, exclude=True)  # Excluded field


class TestBaseDTO:
    """Test suite for BaseDTO."""

    def test_dto_creation(self):
        """Test creating a DTO."""
        now = datetime.now()
        product = ProductDTO(
            id="123", name="Widget", price=29.99, created_at=now, internal_notes="secret"
        )

        assert product.id == "123"
        assert product.name == "Widget"
        assert product.price == 29.99
        assert product.created_at == now

    def test_model_dump(self):
        """Test model_dump functionality."""
        now = datetime.now()
        product = ProductDTO(
            id="123", name="Widget", price=29.99, created_at=now, internal_notes="secret"
        )

        data = product.model_dump()

        # Should include business fields
        assert data["id"] == "123"
        assert data["name"] == "Widget"
        assert data["price"] == 29.99
        assert data["created_at"] == now

        # Should exclude internal_notes (exclude=True)
        assert "internal_notes" not in data

    def test_model_dump_json(self):
        """Test JSON serialization."""
        now = datetime.now()
        product = ProductDTO(id="123", name="Widget", price=29.99, created_at=now)

        json_str = product.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["id"] == "123"
        assert parsed["name"] == "Widget"
        assert parsed["price"] == 29.99

    def test_model_validate(self):
        """Test deserialization from dict."""
        now = datetime.now()
        data = {"id": "456", "name": "Gadget", "price": 19.99, "created_at": now}

        product = ProductDTO.model_validate(data)

        assert product.id == "456"
        assert product.name == "Gadget"
        assert product.price == 19.99
        assert product.created_at == now

    def test_model_validate_json(self):
        """Test deserialization from JSON."""
        json_str = """
        {
            "id": "789",
            "name": "Tool",
            "price": 39.99,
            "created_at": "2024-01-01T10:00:00"
        }
        """

        product = ProductDTO.model_validate_json(json_str)

        assert product.id == "789"
        assert product.name == "Tool"
        assert product.price == 39.99

    def test_field_validation(self):
        """Test field validation rules."""
        now = datetime.now()

        # Should raise validation error for invalid price
        with pytest.raises(ValidationError):
            ProductDTO(
                id="123",
                name="Widget",
                price=-10.0,  # Invalid: price must be > 0
                created_at=now,
            )

        # Should raise validation error for empty name
        with pytest.raises(ValidationError):
            ProductDTO(
                id="123",
                name="",  # Invalid: name must have min_length=1
                price=29.99,
                created_at=now,
            )

    def test_config_applied(self):
        """Test that model config is applied."""
        # Test string stripping
        product = ProductDTO(
            id="123",
            name="  Widget  ",  # Should be stripped
            price=29.99,
            created_at=datetime.now(),
        )

        assert product.name == "Widget"  # Whitespace stripped


class TestListDTO:
    """Test suite for ListDTO."""

    def test_list_dto_creation(self):
        """Test creating a ListDTO."""
        items = [{"id": "1", "name": "Item1"}, {"id": "2", "name": "Item2"}]
        list_dto = ListDTO(items=items, total=100, page=1, page_size=20)

        assert len(list_dto.items) == 2
        assert list_dto.total == 100
        assert list_dto.page == 1
        assert list_dto.page_size == 20

    def test_total_pages_calculation(self):
        """Test total pages calculation."""
        list_dto = ListDTO(items=[], total=100, page=1, page_size=20)

        assert list_dto.total_pages == 5  # 100 / 20 = 5

    def test_total_pages_with_remainder(self):
        """Test total pages with remainder."""
        list_dto = ListDTO(items=[], total=101, page=1, page_size=20)

        assert list_dto.total_pages == 6  # (101 + 20 - 1) // 20 = 6

    def test_has_next_page(self):
        """Test has_next_page property."""
        list_dto = ListDTO(
            items=[],
            total=100,
            page=2,
            page_size=20,  # 5 total pages
        )

        assert list_dto.has_next_page is True  # page 2 of 5

        # Test last page
        list_dto.page = 5
        assert list_dto.has_next_page is False

    def test_has_prev_page(self):
        """Test has_prev_page property."""
        list_dto = ListDTO(items=[], total=100, page=2, page_size=20)

        assert list_dto.has_prev_page is True  # page 2

        # Test first page
        list_dto.page = 1
        assert list_dto.has_prev_page is False

    def test_no_pagination_info(self):
        """Test behavior without pagination info."""
        list_dto = ListDTO(
            items=[],
            total=100,
            # No page/page_size provided
        )

        assert list_dto.total_pages is None
        assert list_dto.has_next_page is False
        assert list_dto.has_prev_page is False


class TestErrorDTO:
    """Test suite for ErrorDTO."""

    def test_error_dto_creation(self):
        """Test creating an ErrorDTO."""
        error = ErrorDTO(code="VALIDATION_ERROR", message="Invalid input data")

        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input data"
        assert error.details is None
        assert isinstance(error.timestamp, datetime)

    def test_error_dto_with_details(self):
        """Test ErrorDTO with details."""
        details = {"field": "name", "constraint": "required"}
        error = ErrorDTO(code="FIELD_ERROR", message="Field validation failed", details=details)

        assert error.details == details

    def test_error_code_uppercase_validation(self):
        """Test that error codes are converted to uppercase."""
        error = ErrorDTO(
            code="validation_error",  # lowercase
            message="Test error",
        )

        assert error.code == "VALIDATION_ERROR"  # Should be uppercase

    def test_custom_timestamp(self):
        """Test setting custom timestamp."""
        custom_time = datetime(2024, 1, 1, 10, 0, 0)
        error = ErrorDTO(code="TEST_ERROR", message="Test message", timestamp=custom_time)

        assert error.timestamp == custom_time

    def test_error_serialization(self):
        """Test error DTO serialization."""
        error = ErrorDTO(code="API_ERROR", message="Something went wrong", details={"status": 500})

        data = error.model_dump()

        assert data["code"] == "API_ERROR"
        assert data["message"] == "Something went wrong"
        assert data["details"]["status"] == 500
        assert "timestamp" in data


class TestDTOIntegration:
    """Integration tests for DTO functionality."""

    def test_nested_dto_serialization(self):
        """Test serialization with nested DTOs."""
        products = [
            ProductDTO(id="1", name="Product1", price=10.0, created_at=datetime.now()),
            ProductDTO(id="2", name="Product2", price=20.0, created_at=datetime.now()),
        ]

        response = ListDTO(
            items=[p.model_dump() for p in products],  # Convert to dict first
            total=2,
            page=1,
            page_size=10,
        )

        json_str = response.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert len(parsed["items"]) == 2
        assert parsed["total"] == 2

    def test_dto_round_trip(self):
        """Test full serialization round trip."""
        original = ProductDTO(
            id="test-123",
            name="Test Product",
            price=99.99,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        restored = ProductDTO.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.price == original.price
