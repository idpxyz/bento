"""Category 仓储接口"""

from typing import Protocol

from bento.core.ids import ID
from bento.persistence.specification import CompositeSpecification

from contexts.catalog.domain.category import Category


class ICategoryRepository(Protocol):
    """Category 仓储协议

    遵循依赖反转原则，Domain/Application 层只依赖此协议。
    Infrastructure 层提供具体实现。

    标准仓储操作（匹配 Bento RepositoryAdapter 签名）：
    - get(id) - 根据 ID 查询聚合根
    - save(aggregate) - 保存聚合根（创建或更新）
    - delete(aggregate) - 删除聚合根
    - list(specification) - 查询列表（支持规约模式）

    注意：Protocol 签名与框架 RepositoryAdapter 完全一致
    """

    async def get(self, id: ID) -> Category | None:
        """根据ID获取聚合根"""
        ...

    async def save(self, aggregate: Category) -> None:
        """保存聚合根（创建或更新）"""
        ...

    async def delete(self, aggregate: Category) -> None:
        """删除聚合根"""
        ...

    async def list(
        self, specification: CompositeSpecification[Category] | None = None
    ) -> list[Category]:
        """查询聚合根列表（支持规约模式）

        Args:
            specification: 可选的查询规约，None 表示查询全部

        Returns:
            Category 列表
        """
        ...


# ============================================================================
# 实现示例（需手动创建，放在 infrastructure/repositories/category_repository_impl.py）
# ============================================================================
#
# from bento.infrastructure.repository import RepositoryAdapter
# from bento.persistence.repository import BaseRepository
# from bento.persistence.interceptor import create_default_chain
# from contexts.catalog.domain.category import Category
# from contexts.catalog.infrastructure.models.category_po import CategoryPO
# from contexts.catalog.infrastructure.mappers.category_mapper import CategoryMapper
#
# class CategoryRepository(RepositoryAdapter[Category, CategoryPO, str]):
#     """Category 仓储实现
#
#     框架自动提供的功能：
#     - 领域对象 <-> 持久化对象映射
#     - 审计字段自动填充（created_at, updated_at, created_by, updated_by）
#     - 拦截器链（缓存、软删除、乐观锁等）
#     """
#
#     def __init__(self, session, actor: str = "system"):
#         mapper = CategoryMapper()
#         base_repo = BaseRepository(
#             session=session,
#             po_type=CategoryPO,
#             actor=actor,
#             interceptor_chain=create_default_chain(actor)
#         )
#         super().__init__(repository=base_repo, mapper=mapper)
#
