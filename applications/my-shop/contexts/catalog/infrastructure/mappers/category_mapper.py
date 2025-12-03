"""Category 映射器接口"""

from typing import Protocol

from bento.application.mappers import AutoMapper

from contexts.catalog.domain.category import Category
from contexts.catalog.infrastructure.models.category_po import CategoryPO


class ICategoryMapper(Protocol):
    """Category 映射器协议

    负责领域对象与持久化对象之间的双向映射。
    Infrastructure 层提供具体实现。
    """

    def to_po(self, domain_obj: Category) -> CategoryPO:
        """领域对象 -> 持久化对象"""
        ...

    def to_domain(self, po: CategoryPO) -> Category:
        """持久化对象 -> 领域对象"""
        ...


# ============================================================================
# 实现
# ============================================================================


class CategoryMapper(AutoMapper[Category, CategoryPO]):
    """Category 映射器实现 - 使用 Bento 框架 AutoMapper"""

    def __init__(self):
        """初始化 AutoMapper"""
        super().__init__(
            domain_type=Category,
            po_type=CategoryPO,
        )

        # 忽略审计和元数据字段（由 Interceptor 处理）
        self.ignore_fields(
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
            "deleted_by",
            "version",
        )


# ============================================================================
# 实现示例（需手动创建）
# ============================================================================
#
# from bento.application.mapper import AutoMapper
# from contexts.catalog.domain.category import Category
# from contexts.catalog.infrastructure.models.category_po import CategoryPO
#
# class CategoryMapper(AutoMapper[Category, CategoryPO]):
#     """Category 映射器实现 - 使用框架 AutoMapper
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
