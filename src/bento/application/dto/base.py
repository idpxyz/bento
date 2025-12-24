"""Pydantic-based DTO classes for Bento Framework.

This module provides base classes and utilities for Data Transfer Objects (DTOs)
using Pydantic's full power and performance.

Key Features:
- High-performance serialization/deserialization (Rust core)
- Automatic type validation and coercion
- Built-in JSON support with custom encoders
- FastAPI integration with automatic OpenAPI docs
- Enterprise-grade field validation
- Zero boilerplate - leverage Pydantic's native methods
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class BaseDTO(BaseModel):
    """Base class for all Data Transfer Objects.

    Leverages Pydantic's native capabilities instead of reinventing the wheel.

    Key Methods (All Built-in):
    - model_dump() -> dict           # Replace manual to_dict()
    - model_dump_json() -> str       # Replace manual to_json()
    - model_validate(data) -> Self   # Replace manual from_dict()
    - model_validate_json(json) -> Self  # Replace manual from_json()

    Example:
        ```python
        class ProductDTO(BaseDTO):
            id: str = Field(..., description="Product identifier")
            name: str = Field(..., min_length=1, description="Product name")
            price: float = Field(..., gt=0, description="Product price")
            created_at: datetime
            internal_notes: Optional[str] = Field(None, exclude=True)  # Auto-excluded

        # Usage - All Pydantic native methods
        product = ProductDTO(
            id="123",
            name="Widget",
            price=29.99,
            created_at=datetime.now()
        )

        # Serialization (built-in, high-performance)
        dict_data = product.model_dump()                    # Dict
        json_str = product.model_dump_json()               # JSON string
        clean_data = product.model_dump(exclude_none=True) # Exclude None values

        # Deserialization (built-in, with validation)
        product2 = ProductDTO.model_validate(dict_data)      # From dict
        product3 = ProductDTO.model_validate_json(json_str)  # From JSON

        # Field access and validation happen automatically
        print(product.name)  # Always validated and type-safe
        ```
    """

    # Global configuration for all DTOs
    model_config = ConfigDict(
        # Performance optimizations
        str_strip_whitespace=True,  # Auto-strip whitespace
        validate_assignment=True,  # Validate on field assignment
        use_enum_values=True,  # Serialize enums to values
        # API integration
        populate_by_name=True,  # Support field aliases
        extra="forbid",  # Strict mode - no extra fields
        # Documentation support
        arbitrary_types_allowed=False,  # Keep types JSON-serializable
        # Serialization mode (Pydantic v2)
        ser_json_timedelta="iso8601",
    )


class ListDTO(BaseDTO):
    """Standard paginated list response DTO.

    Provides consistent structure for list endpoints with pagination metadata.

    Example:
        ```python
        products = [ProductDTO(...), ProductDTO(...)]
        response = ListDTO[ProductDTO](
            items=products,
            total=100,
            page=1,
            page_size=20
        )

        # Automatic serialization
        json_response = response.model_dump_json()

        # Type-safe access
        first_item: ProductDTO = response.items[0]  # Type checked!
        total_pages: int = response.total_pages     # Computed field
        ```
    """

    items: list[Any] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int | None = Field(None, ge=1, description="Current page number")
    page_size: int | None = Field(None, ge=1, description="Items per page")

    @computed_field  # Pydantic computed property
    @property
    def total_pages(self) -> int | None:
        """Calculate total pages automatically."""
        if self.page is None or self.page_size is None or self.page_size == 0:
            return None
        return (self.total + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next_page(self) -> bool:
        """Check if there's a next page."""
        if not self.total_pages or not self.page:
            return False
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev_page(self) -> bool:
        """Check if there's a previous page."""
        return self.page is not None and self.page > 1


class ErrorDTO(BaseDTO):
    """Standard error response DTO.

    Provides consistent error format across the application with automatic
    timestamp and structured details.

    Example:
        ```python
        # Simple error
        error = ErrorDTO(
            code="VALIDATION_ERROR",
            message="Invalid input data"
        )

        # Detailed error with context
        error = ErrorDTO(
            code="FIELD_VALIDATION_ERROR",
            message="Field validation failed",
            details={
                "field": "price",
                "constraint": "must be greater than 0",
                "provided_value": -5
            }
        )

        # Automatic JSON serialization for APIs
        error_json = error.model_dump_json()
        ```
    """

    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error context")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error occurrence time")

    # Custom validation example (Pydantic v2 syntax)
    @field_validator("code")
    @classmethod
    def code_must_be_uppercase(cls, v: str) -> str:
        """Ensure error codes are uppercase for consistency."""
        return v.upper()


# Type aliases for common patterns
PaginatedResponse = ListDTO  # Backward compatibility alias


# Simple operation result DTOs (without audit fields)
# Note: Audit fields (created_at, updated_at, etc.) are handled automatically
# by the persistence layer's Mixin + Interceptor system, not at the DTO level.


class CreatedDTO(BaseDTO):
    """Standard response for creation operations.

    Only includes business-relevant data. Audit fields like created_at
    are automatically handled by AuditFieldsMixin + AuditInterceptor
    at the persistence layer.
    """

    id: str = Field(..., description="Created resource identifier")


class UpdatedDTO(BaseDTO):
    """Standard response for update operations.

    Only includes business-relevant data. Audit tracking is handled
    automatically by the persistence layer.
    """

    id: str = Field(..., description="Updated resource identifier")


class DeletedDTO(BaseDTO):
    """Standard response for deletion operations.

    Only includes business-relevant data. Soft delete timestamps
    are handled by SoftDeleteFieldsMixin + SoftDeleteInterceptor.
    """

    id: str = Field(..., description="Deleted resource identifier")


# Integration helpers for ApplicationService
def to_application_service_result(dto: BaseDTO, success: bool = True) -> dict[str, Any]:
    """Helper to integrate DTOs with ApplicationServiceResult.

    Example:
        ```python
        class CreateProductService(ApplicationService[CreateProductCommand, ProductDTO]):
            async def handle(self, command: CreateProductCommand) -> ProductDTO:
                # Business logic...
                return ProductDTO(id=str(product.id), name=product.name, ...)

        # The DTO automatically serializes for API responses
        result = await service.execute(command)
        if result.is_success:
            api_response = result.data.model_dump_json()  # Perfect for FastAPI!
        ```
    """
    return {
        "is_success": success,
        "data": dto.model_dump() if success else None,
        "error": None if success else dto.model_dump(),
    }
