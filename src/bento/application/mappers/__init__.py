"""Enterprise Mapper System for Bento Framework.

This module provides professional mapping strategies to transform between
Domain objects and Persistence objects with minimal code.

Core Mappers (Choose based on your needs):
- AutoMapper: Zero-config automatic mapping (90% use cases) ⭐
- BaseMapper: Manual mapping with helper methods (10% use cases)

Architecture:
    All mappers implement the Mapper protocol from
    bento.application.ports.mapper, providing bidirectional
    Domain ↔ PO transformation with automatic:
    - ID conversion (EntityId/ID ↔ str)
    - Enum conversion (Enum ↔ str)
    - Child entity mapping
    - Event cleanup

Example:
    ```python
    # 90% use case - AutoMapper (zero config!)
    class OrderMapper(AutoMapper[Order, OrderModel]):
        def __init__(self):
            super().__init__(Order, OrderModel)
            self.register_child("items", OrderItemMapper())
        # Done! Everything else is automatic

    # 10% use case - BaseMapper (when you need control)
    class OrderMapper(BaseMapper[Order, OrderModel]):
        def map(self, domain: Order) -> OrderModel:
            return OrderModel(
                id=self.convert_id_to_str(domain.id),  # Helper
                status=self.convert_enum_to_str(domain.status),  # Helper
                ...
            )
    ```

Benefits:
    - 90% less code compared to manual mapping
    - Type-safe with full IDE support
    - Automatic adaptation to schema changes
    - Consistent patterns across all mappers

See Also:
    - bento.application.ports.mapper: Protocol definitions
    - order_mapper_auto.py: Complete example using AutoMapper
    - order_mapper_smart.py: Complete example using BaseMapper
"""

from bento.application.mappers.auto import AutoMapper
from bento.application.mappers.base import BaseMapper, MappingContext
from bento.application.mappers.strategy import MapperStrategy

__all__ = [
    "MapperStrategy",  # Base class for all mappers
    "BaseMapper",  # Manual mapping with helper methods
    "MappingContext",  # Optional context for propagating tenant/org/actor info
    "AutoMapper",  # Zero-config automatic mapping (recommended) ⭐
]
