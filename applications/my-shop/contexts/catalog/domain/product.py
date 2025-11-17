"""Product 聚合根"""

from dataclasses import dataclass

from bento.domain.aggregate import AggregateRoot


@dataclass
class Product(AggregateRoot):
    """Product 聚合根

    开发人员只需要：
    1. 定义字段
    2. 实现业务方法

    框架自动处理：
    - 事件收集（调用 add_event）
    - 持久化（Repository）
    - 事务管理（UnitOfWork）
    """

    id: str
    name: str
    description: str
    price: float
    category_id: str | None = None  # 所属分类（可选）

    def __post_init__(self):
        super().__init__(id=self.id)

    def assign_to_category(self, category_id: str) -> None:
        """将产品分配到指定分类"""
        if not category_id:
            raise ValueError("Category ID cannot be empty")
        self.category_id = category_id

    def remove_from_category(self) -> None:
        """从分类中移除产品"""
        self.category_id = None

    def is_categorized(self) -> bool:
        """检查产品是否已分类"""
        return self.category_id is not None

    def change_price(self, new_price: float) -> None:
        """修改价格（带验证）"""
        if new_price <= 0:
            raise ValueError("Price must be greater than 0")
        self.price = new_price
