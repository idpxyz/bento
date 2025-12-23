"""Product 聚合根 - 智能 ID 处理"""

from dataclasses import dataclass

from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot

from ..events.productcreated_event import ProductCreated


@dataclass
class Product(AggregateRoot):
    """Product 聚合根（增强版）

    ✅ 智能 ID 处理：
    - 使用 Bento 标准 ID 类型
    - 自动序列化/反序列化
    - 类型安全

    ✅ 增强字段：
    - sku: 商品唯一编码（用于测试唯一性检查）
    - brand: 品牌（用于测试多字段分组）
    - stock: 库存（用于测试数值聚合）
    - is_active: 状态（用于测试条件过滤）
    - sales_count: 销量（用于测试排序）

    框架自动处理：
    - 事件收集（调用 add_event）
    - 持久化（Repository）
    - 事务管理（UnitOfWork）
    """

    id: ID  # ✅ 使用标准 ID 类型
    name: str
    description: str
    price: float

    # 扩展字段
    sku: str | None = None  # SKU 商品编码
    brand: str | None = None  # 品牌
    stock: int = 0  # 库存数量
    is_active: bool = True  # 是否上架
    sales_count: int = 0  # 销量

    category_id: ID | None = None  # ✅ 分类 ID 也使用标准类型

    @classmethod
    def create(
        cls,
        id: ID,
        name: str,
        description: str,
        price: float,
        stock: int = 0,
        sku: str | None = None,
        brand: str | None = None,
        is_active: bool = True,
        category_id: ID | None = None,
    ) -> "Product":
        """工厂方法：创建新产品并触发 ProductCreated 事件"""
        product = cls(
            id=id,
            name=name,
            description=description,
            price=price,
            stock=stock,
            sku=sku,
            brand=brand,
            is_active=is_active,
            category_id=category_id,
        )

        # 触发领域事件
        event = ProductCreated(
            product_id=str(id),
            name=name,
            price=price,
            sku=sku,
            brand=brand,
        )
        product.add_event(event)

        return product

    def __post_init__(self):
        super().__init__(id=str(self.id))  # ✅ ID 自动转字符串

    def assign_to_category(self, category_id: ID) -> None:
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

    def move_to(self, new_parent_id: ID | None) -> None:
        """移动到新的父分类"""
        self.parent_id = new_parent_id

    def change_price(self, new_price: float) -> None:
        """修改价格（带验证）"""
        if new_price <= 0:
            raise ValueError("Price must be greater than 0")
        self.price = new_price

    def set_sku(self, sku: str) -> None:
        """设置 SKU"""
        if not sku or not sku.strip():
            raise ValueError("SKU cannot be empty")
        self.sku = sku.strip()

    def set_brand(self, brand: str) -> None:
        """设置品牌"""
        self.brand = brand

    def update_stock(self, quantity: int) -> None:
        """更新库存"""
        if self.stock + quantity < 0:
            raise ValueError("Insufficient stock")
        self.stock += quantity

    def set_stock(self, quantity: int) -> None:
        """设置库存"""
        if quantity < 0:
            raise ValueError("Stock cannot be negative")
        self.stock = quantity

    def activate(self) -> None:
        """上架"""
        self.is_active = True

    def deactivate(self) -> None:
        """下架"""
        self.is_active = False

    def record_sale(self, quantity: int = 1) -> None:
        """记录销售"""
        self.sales_count += quantity
        self.update_stock(-quantity)

    def is_in_stock(self) -> bool:
        """检查是否有库存"""
        return self.stock > 0

    def is_low_stock(self, threshold: int = 10) -> bool:
        """检查是否低库存"""
        return 0 < self.stock <= threshold
