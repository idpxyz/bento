"""Order Mapper 实现 - 处理 Order + OrderItem 聚合映射"""

from bento.application.mapper import AutoMapper

from contexts.ordering.domain.order import Order
from contexts.ordering.domain.orderitem import OrderItem
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO


class OrderMapper(AutoMapper[Order, OrderPO]):
    """Order Mapper - 使用 Bento AutoMapper

    AutoMapper 自动处理：
    - 同名字段映射
    - OrderStatus enum 转换
    - 审计字段由 Interceptor 处理（ignored）

    注意：items 集合需要在 Repository 层单独处理
    """

    def __init__(self):
        super().__init__(
            domain_type=Order,
            po_type=OrderPO,
        )

        # 忽略审计和元数据字段（由 Interceptor 自动处理）
        self.ignore_fields(
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "version",
            "deleted_at",
            "deleted_by",
        )

        # items 集合在 Repository 层处理
        self.ignore_fields("items")


# OrderItem Mapper（简单映射，审计字段由 Interceptor 处理）
class OrderItemMapper(AutoMapper[OrderItem, OrderItemPO]):
    """OrderItem Mapper - 使用 AutoMapper"""

    def __init__(self):
        super().__init__(
            domain_type=OrderItem,
            po_type=OrderItemPO,
        )

        # 忽略审计字段
        self.ignore_fields(
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "version",
            "deleted_at",
            "deleted_by",
        )
