"""{{Name}} 仓储接口"""
from typing import Protocol

from bento.core.ids import ID
from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}


class I{{Name}}Repository(Protocol):
    """{{Name}} 仓储协议

    遵循依赖反转原则，Domain/Application 层只依赖此协议。
    Infrastructure 层提供具体实现。

    标准仓储操作：
    - get(id) - 根据 ID 查询聚合根（返回聚合根或 None）
    - save(aggregate) - 保存聚合根（创建或更新，返回保存后的聚合根）
    - delete(id) - 删除聚合根
    - find_all(specification) - 查询列表（支持 Specification）
    - exists(id) - 检查是否存在
    """

    async def get(self, id: ID) -> {{Name}} | None:
        """根据 ID 获取聚合根
        
        Args:
            id: 聚合根 ID
            
        Returns:
            聚合根对象或 None（不存在时）
        """
        ...

    async def save(self, aggregate: {{Name}}) -> {{Name}}:
        """保存聚合根（创建或更新）
        
        Args:
            aggregate: 聚合根对象
            
        Returns:
            保存后的聚合根（支持链式调用）
        """
        ...

    async def delete(self, id: ID) -> None:
        """删除聚合根
        
        Args:
            id: 聚合根 ID
        """
        ...

    async def find_all(self, specification=None) -> list[{{Name}}]:
        """查询聚合根列表
        
        Args:
            specification: 可选的查询条件
            
        Returns:
            聚合根列表
        """
        ...

    async def exists(self, id: ID) -> bool:
        """检查聚合根是否存在
        
        Args:
            id: 聚合根 ID
            
        Returns:
            True 如果存在，否则 False
        """
        ...


# ============================================================================
# 实现示例（使用 Bento Framework 的 RepositoryAdapter）
# ============================================================================
#
# 创建文件：infrastructure/repositories/{{name_lower}}_repository.py
#
# from bento.infrastructure.repository.adapter import RepositoryAdapter
# from bento.persistence.repository.sqlalchemy import BaseRepository
# from bento.persistence.interceptor import create_default_chain
# from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}
# from contexts.{{context}}.infrastructure.models.{{name_lower}}_po import {{Name}}PO
# from contexts.{{context}}.infrastructure.mappers.{{name_lower}}_mapper import {{Name}}Mapper
#
# class {{Name}}Repository(RepositoryAdapter[{{Name}}, {{Name}}PO, str]):
#     """{{Name}} 仓储实现
#
#     Bento Framework 自动提供的功能：
#     1. 领域对象 <-> 持久化对象映射（通过 Mapper）
#     2. 审计字段自动填充（created_at, updated_at, created_by, updated_by）
#     3. 拦截器链（缓存、软删除、乐观锁等）
#     4. 事务管理（通过 UnitOfWork）
#     5. 领域事件自动收集和发布
#
#     使用方式：
#         # 在 Application Service 中
#         {{name_lower}}_repo = uow.repository({{Name}})
#         {{name_lower}} = await {{name_lower}}_repo.get({{name_lower}}_id)
#         await {{name_lower}}_repo.save({{name_lower}})
#     """
#
#     def __init__(self, session, actor: str = "system"):
#         """初始化仓储
#         
#         Args:
#             session: SQLAlchemy Session
#             actor: 操作者标识（用于审计字段）
#         """
#         mapper = {{Name}}Mapper()
#         base_repo = BaseRepository(
#             session=session,
#             po_type={{Name}}PO,
#             actor=actor,
#             interceptor_chain=create_default_chain(actor)
#         )
#         super().__init__(repository=base_repo, mapper=mapper)
#
