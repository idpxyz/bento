"""{{Name}} 仓储接口"""
from typing import Protocol
from domain.{{name_lower}} import {{Name}}


class I{{Name}}Repository(Protocol):
    """{{Name}} 仓储协议

    遵循依赖反转原则，Domain/Application 层只依赖此协议。
    Infrastructure 层提供具体实现。

    标准仓储操作：
    - get(id) - 根据 ID 查询聚合根
    - save(entity) - 保存聚合根（创建或更新）
    - delete(id) - 删除聚合根
    - list() - 查询列表
    - exists(id) - 检查是否存在
    """

    async def get(self, id: str) -> {{Name}} | None:
        """根据ID获取聚合根"""
        ...

    async def save(self, entity: {{Name}}) -> None:
        """保存聚合根（创建或更新）"""
        ...

    async def delete(self, id: str) -> None:
        """删除聚合根"""
        ...

    async def list(self, limit: int = 100, offset: int = 0) -> list[{{Name}}]:
        """查询聚合根列表"""
        ...

    async def exists(self, id: str) -> bool:
        """检查聚合根是否存在"""
        ...


# ============================================================================
# 实现示例（需手动创建，放在 infrastructure/repositories/{{name_lower}}_repository_impl.py）
# ============================================================================
#
# from bento.infrastructure.repository import RepositoryAdapter
# from bento.persistence.repository import BaseRepository
# from bento.persistence.interceptor import create_default_chain
# from domain.{{name_lower}} import {{Name}}
# from infrastructure.models.{{name_lower}}_po import {{Name}}PO
# from infrastructure.mappers.{{name_lower}}_mapper import {{Name}}Mapper
#
# class {{Name}}Repository(RepositoryAdapter[{{Name}}, {{Name}}PO, str]):
#     """{{Name}} 仓储实现
#
#     框架自动提供的功能：
#     - 领域对象 <-> 持久化对象映射
#     - 审计字段自动填充（created_at, updated_at, created_by, updated_by）
#     - 拦截器链（缓存、软删除、乐观锁等）
#     """
#
#     def __init__(self, session, actor: str = "system"):
#         mapper = {{Name}}Mapper()
#         base_repo = BaseRepository(
#             session=session,
#             po_type={{Name}}PO,
#             actor=actor,
#             interceptor_chain=create_default_chain(actor)
#         )
#         super().__init__(repository=base_repo, mapper=mapper)
#
