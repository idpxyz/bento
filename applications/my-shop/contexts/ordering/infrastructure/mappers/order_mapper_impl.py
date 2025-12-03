"""Order Mapper 实现 - 零配置智能映射

✅ 框架改进后的超简化版本：
- AutoMapper 自动处理 ID ↔ str 转换
- 自动处理 Enum 转换
- 自动忽略审计字段
- 无需手动编写任何转换逻辑
"""

from bento.application.mappers.auto import AutoMapper

from contexts.ordering.domain.models.order import Order
from contexts.ordering.domain.models.orderitem import OrderItem
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO


class OrderMapper(AutoMapper[Order, OrderPO]):
    """Order Mapper - 零配置智能映射

    ✅ 框架自动处理：
    - ID(uuid) ↔ str 双向转换
    - OrderStatus enum ↔ str 转换
    - 审计字段自动忽略
    - 同名字段自动映射
    """

    def __init__(self):
        super().__init__(Order, OrderPO)

        # ✅ 只需要配置业务规则，技术细节由框架处理
        self.ignore_fields("items")  # 聚合子实体在 Repository 层处理


class OrderItemMapper(AutoMapper[OrderItem, OrderItemPO]):
    """OrderItem Mapper - 零配置智能映射

    ✅ 继承即用，无需任何配置
    """

    def __init__(self):
        super().__init__(OrderItem, OrderItemPO)
        # ✅ 完全零配置：框架自动处理所有字段映射
