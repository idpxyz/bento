"""Order domain-to-persistence mapper using AutoMapper.

This mapper handles bidirectional conversion between:
- Order (domain aggregate) ↔ OrderModel (persistence object)
- OrderItem (domain entity) ↔ OrderItemModel (persistence object)

Key features:
- Zero-config automatic mapping via type analysis
- Automatic ID/Enum conversion
- Automatic child entity mapping
- Automatic event cleanup

Note:
    Audit fields (created_at, updated_at, etc.) are populated by Interceptors.
"""

from applications.ecommerce.modules.order.domain.order import Order, OrderItem
from applications.ecommerce.modules.order.persistence.models import OrderItemModel, OrderModel
from bento.application.mapper import AutoMapper


class OrderItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    """Mapper for OrderItem ↔ OrderItemModel conversion.

    Framework automatically handles:
    - id: EntityId ↔ str
    - product_id: ID ↔ str
    - product_name, quantity, unit_price: direct copy
    """

    def __init__(self) -> None:
        """Initialize with automatic type analysis."""
        super().__init__(OrderItem, OrderItemModel)
        # order_id will be set by parent mapper
        self.ignore_fields("order_id")


class OrderMapper(AutoMapper[Order, OrderModel]):
    """Mapper for Order ↔ OrderModel conversion.

    Framework automatically handles:
    - id, customer_id: ID ↔ str
    - status: OrderStatus (Enum) ↔ str
    - paid_at, cancelled_at: datetime (direct copy)
    - items: automatic child mapping via registered mapper
    - Event cleanup after map_reverse

    Example:
        ```python
        mapper = OrderMapper()

        # Domain to Persistence
        order = Order(order_id=ID.generate(), customer_id=customer_id)
        order_model = mapper.map(order)

        # Persistence to Domain
        order_model = session.get(OrderModel, order_id)
        order = mapper.map_reverse(order_model)
        ```
    """

    def __init__(self) -> None:
        """Initialize with automatic type analysis and child registration."""
        super().__init__(Order, OrderModel)
        # Register child entity mapper - items are automatically mapped
        self.register_child("items", OrderItemMapper(), parent_keys="order_id")
