"""Product 映射器接口"""

from typing import Protocol

from domain.product import Product
from infrastructure.models.product_po import ProductPO


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
# 实现示例（需手动创建）
# ============================================================================
#
# from bento.application.mapper import AutoMapper
# from domain.product import Product
# from infrastructure.models.product_po import ProductPO
#
# class ProductMapper(AutoMapper[Product, ProductPO]):
#     """Product 映射器实现 - 使用框架 AutoMapper
#
#     框架自动推断字段映射：
#     - 同名字段自动映射
#     - ID 类型转换（str ↔ EntityId）
#     - Enum 转换（Enum ↔ str/int）
#     - 可选字段处理（Optional）
#     - 嵌套对象递归映射
#
#     如需自定义映射逻辑，可重写：
#     - to_po(domain_obj) -> po_obj
#     - to_domain(po_obj) -> domain_obj
#     """
#     pass
#
