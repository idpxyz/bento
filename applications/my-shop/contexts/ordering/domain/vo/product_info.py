"""ProductInfo 值对象 - Ordering Context 的产品信息快照

这不是 Product 聚合根的引用，而是 Ordering Context 需要的产品信息副本。
符合 DDD 原则：每个 BC 维护自己需要的数据视图。

位置说明：
- 值对象（Value Object）应该放在 domain/vo/ 目录
- 这是 DDD 的标准做法，便于组织和管理
"""

from dataclasses import dataclass

from bento.domain import CompositeValueObject


@dataclass(frozen=True)
class ProductInfo(CompositeValueObject):
    """产品信息值对象

    订单上下文只关心创建订单时需要的产品属性：
    - 产品是否存在
    - 产品是否可用
    - 产品的基本信息（用于显示）

    不关心：
    - 产品的分类、库存管理等 Catalog Context 的内部细节

    使用示例：
        ```python
        info = ProductInfo.create(
            product_id="prod-123",
            product_name="iPhone 15",
            unit_price=999.0,
            is_available=True
        )
        data = info.to_dict()  # 序列化
        info2 = ProductInfo.from_dict(data)  # 反序列化
        ```
    """

    product_id: str
    product_name: str
    unit_price: float
    is_available: bool = True

    def validate(self) -> None:
        """验证值对象的不变式"""
        if not self.product_id or not self.product_id.strip():
            raise ValueError("产品ID不能为空")

        if not self.product_name or not self.product_name.strip():
            raise ValueError("产品名称不能为空")

        if self.unit_price < 0:
            raise ValueError("产品价格不能为负数")
