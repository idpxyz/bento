"""Order DTO Mapper - Using Bento AutoMapper! 🎉"""

from bento.application.dto.auto_mapper import AutoMapper

from contexts.ordering.application.dto import OrderDTO, OrderItemDTO
from contexts.ordering.domain.models.order import Order, OrderItem


class OrderItemDTOMapper(AutoMapper[OrderItem, OrderItemDTO]):
    """OrderItem DTO Mapper - Zero Configuration! 🤖

    Uses Bento's AutoMapper (same as Domain↔PO mapping):
    - ✅ id, product_id: ID → str (automatic)
    - ✅ product_name, quantity, unit_price, subtotal: direct mapping (automatic)

    Compare:
    Before: 15+ lines of manual field mapping
    After:  4 lines total! 🎊
    """

    def __init__(self):
        super().__init__(OrderItem, OrderItemDTO)
        # All fields auto-mapped! No configuration needed! ✨


class OrderDTOMapper(AutoMapper[Order, OrderDTO]):
    """Order DTO Mapper - Smart Automation! 🤖

    Uses Bento's AutoMapper with custom logic only where needed:
    - ✅ id, customer_id, total, dates: ID/direct mapping (automatic)
    - ✅ status: Enum → value (custom override)
    - ✅ items: nested OrderItem mapping (custom override)

    Compare:
    Before: 30+ lines of manual mapping + error-prone field iteration
    After:  8 lines total! 🎊
    """

    def __init__(self):
        super().__init__(Order, OrderDTO)
        self.item_mapper = OrderItemDTOMapper()

        # ✅ 增强映射 - 包含嵌套对象和计算字段
        self.field_mappings = {
            "items": lambda order: self.item_mapper.to_dto_list(order.items),  # Nested mapping
            "item_count": lambda order: len(order.items),  # 计算字段
            "status_display": lambda order: order.status.value.replace(
                "_", " "
            ).title(),  # 格式化状态
            "created_at_str": lambda order: order.created_at.isoformat()
            if order.created_at
            else None,
            "is_paid": lambda order: order.status.value in ["paid", "shipped", "delivered"],
            "can_cancel": lambda order: order.status.value in ["pending", "paid"],
            "formatted_total": lambda order: f"${order.total:.2f}",
        }
