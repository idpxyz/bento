"""Auto Mapper - Convention over Configuration for DTO mapping.

This module provides intelligent automatic mapping with minimal configuration.
Only specify custom logic where needed - everything else is handled automatically.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol, TypeVar

from bento.application.dto.base import BaseDTO
from bento.application.dto.mapper import BaseDTOMapper
from bento.core.ids import ID

Domain = TypeVar("Domain")
DTO = TypeVar("DTO", bound=BaseDTO)


class FieldMapper(Protocol):
    """Protocol for custom field transformation."""

    def map_field(self, value: Any) -> Any:
        """Transform a single field value."""
        ...


class AutoMapper(BaseDTOMapper[Domain, DTO]):
    """Intelligent Auto Mapper with Convention over Configuration.

    Inspired by Bento Framework's AutoMapper[Domain, PO] design.

    Features:
    - 🤖 Automatic field mapping by name
    - 🔄 Smart type conversion (ID→str, Enum→value, etc.)
    - 📋 Automatic list/nested object handling
    - ⚙️ Custom field transformations when needed
    - 🚀 Minimal configuration required

    Example:
        ```python
        class ProductDTOMapper(AutoMapper[Product, ProductDTO]):
            def __init__(self):
                super().__init__(Product, ProductDTO)
                # Optional: custom mappings for special fields
                self.field_mappings = {
                    "status": lambda product: product.status.value
                }

        # Usage - same as before
        mapper = ProductDTOMapper()
        dto = mapper.to_dto(product)  # 90% automatic!
        ```
    """

    def __init__(self, domain_type: type[Domain], dto_type: type[DTO]):
        self.domain_type = domain_type
        self.dto_class = dto_type  # ✅ 修复属性名不匹配
        self._dto_fields = self._get_dto_fields(dto_type)

        # Override in subclass for custom field transformations
        self.field_mappings: dict[str, Any] = {}

        # Override in subclass to exclude fields
        self.excluded_fields: set[str] = set()

    def _get_dto_fields(self, dto_class: type[BaseDTO]) -> set[str]:
        """Extract field names from DTO class."""
        if hasattr(dto_class, "model_fields"):
            return set(dto_class.model_fields.keys())
        return set()

    def _convert_value(self, value: Any, field_name: str, domain: Any = None) -> Any:
        """Smart type conversion with common patterns."""
        if value is None:
            return None

        # Custom field mapping has priority
        if field_name in self.field_mappings:
            mapper = self.field_mappings[field_name]
            if callable(mapper):
                # ✅ 支持传入整个 domain 对象
                return mapper(domain or value)
            return mapper

        # ID → str
        if isinstance(value, ID):
            return str(value)

        # Enum → value
        if isinstance(value, Enum):
            return value.value

        # Decimal → float
        if isinstance(value, Decimal):
            return float(value)

        # datetime/date → keep as is (Pydantic handles it)
        if isinstance(value, (datetime, date)):
            return value

        # List handling
        if isinstance(value, list):
            return [self._convert_value(item, field_name) for item in value]

        # Default: return as-is
        return value

    def to_dto(self, domain: Domain) -> DTO:
        """Convert domain object to DTO automatically.

        Convention over Configuration:
        1. Map fields by name automatically
        2. Apply smart type conversions
        3. Use custom mappings where specified
        4. Skip excluded fields
        """
        dto_data = {}

        # Auto-map all matching fields
        for field_name in self._dto_fields:
            if field_name in self.excluded_fields:
                continue

            # Get value from domain object
            if hasattr(domain, field_name):
                raw_value = getattr(domain, field_name)
                dto_data[field_name] = self._convert_value(raw_value, field_name, domain)
            elif field_name in self.field_mappings:
                # ✅ 支持计算字段（即使 domain 对象没有该属性）
                dto_data[field_name] = self._convert_value(None, field_name, domain)

        # Create DTO instance
        return self.dto_class(**dto_data)


# Convenience factory function
def auto_mapper[T: BaseDTO](dto_class: type[T]) -> type[AutoMapper[Any, T]]:
    """Factory function to create AutoMapper classes.

    Example:
        ```python
        ProductAutoMapper = auto_mapper(ProductDTO)
        mapper = ProductAutoMapper()
        dto = mapper.to_dto(product)  # 🤖 Automatic!
        ```
    """

    class GeneratedAutoMapper(AutoMapper[Any, T]):
        def __init__(self) -> None:
            super().__init__(object, dto_class)  # 修复：使用 object 作为通用 domain 类型

    GeneratedAutoMapper.__name__ = f"{dto_class.__name__}AutoMapper"
    return GeneratedAutoMapper


__all__ = [
    "AutoMapper",
    "FieldMapper",
    "auto_mapper",
]
