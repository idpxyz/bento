"""Product 映射器接口"""

from typing import Protocol

from bento.application.mappers import AutoMapper

from contexts.catalog.domain.models.product import Product
from contexts.catalog.infrastructure.models.product_po import ProductPO


class IProductMapper(Protocol):
    """Product 映射器协议

    负责领域对象与持久化对象之间的双向映射。
    Infrastructure 层提供具体实现。
    """

    def to_po(self, domain_obj: Product) -> ProductPO:
        """领域对象 -> 持久化对象"""
        ...

    def to_domain(self, po: ProductPO) -> Product:
        """持久化对象 -> 领域对象"""
        ...


# ============================================================================
# 实现
# ============================================================================


class ProductMapper(AutoMapper[Product, ProductPO]):
    """Product 映射器实现 - 使用 Bento 框架 AutoMapper

    零配置自动映射：
    - Product.id ↔ ProductPO.id (自动)
    - Product.name ↔ ProductPO.name (自动)
    - Product.price ↔ ProductPO.price (自动)
    等等...

    框架自动推断字段映射：
    - 同名字段自动映射
    - ID 类型转换（str ↔ EntityId）
    - Enum 转换（Enum ↔ str/int）
    - 可选字段处理（Optional）
    - 嵌套对象递归映射

    审计字段由 AuditInterceptor 自动处理，无需手动映射。
    """

    def __init__(self):
        """初始化 AutoMapper"""
        super().__init__(
            domain_type=Product,
            po_type=ProductPO,
        )

        # 忽略审计和元数据字段（由 Interceptor 处理）
        self.ignore_fields(
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "version",
            "deleted_at",
            "deleted_by",
        )
