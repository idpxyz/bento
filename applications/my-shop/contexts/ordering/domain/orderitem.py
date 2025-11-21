"""OrderItem 实体"""

from __future__ import annotations

from dataclasses import dataclass

from bento.core.ids import ID
from bento.domain.entity import Entity


@dataclass
class OrderItem(Entity):
    """OrderItem 实体

    订单项是 Order 聚合的一部分，代表订单中的一个商品。
    作为聚合内的实体，它不应该单独持久化，而是作为 Order 的一部分存储。

    业务规则：
    - 数量必须大于 0
    - 单价不能为负数
    - 小计 = 数量 × 单价
    """

    id: ID
    order_id: str  # 仍然是 str，因为这是外键引用
    product_id: str
    product_name: str
    quantity: int
    unit_price: float

    def __post_init__(self):
        self._validate()

    def _validate(self):
        """验证订单项数据"""
        # Product ID 验证（兼容字符串和ID对象）
        product_id_str = str(self.product_id) if self.product_id else ""
        if not product_id_str or not product_id_str.strip():
            raise ValueError("产品ID不能为空")

        # Product Name 验证
        if not self.product_name or not self.product_name.strip():
            raise ValueError("产品名称不能为空")

        # Quantity 验证
        if self.quantity <= 0:
            raise ValueError("数量必须大于0")

        # Unit Price 验证
        if self.unit_price < 0:
            raise ValueError("单价不能为负数")

    @property
    def subtotal(self) -> float:
        """计算小计金额"""
        return self.quantity * self.unit_price

    def update_quantity(self, new_quantity: int):
        """更新数量"""
        if new_quantity <= 0:
            raise ValueError("数量必须大于0")
        self.quantity = new_quantity

    def update_price(self, new_price: float):
        """更新单价（如促销价格变动）"""
        if new_price < 0:
            raise ValueError("单价不能为负数")
        self.unit_price = new_price
