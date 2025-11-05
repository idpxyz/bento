from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar

from idp.framework.infrastructure.persistence.specification.core.base import (
    Specification,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    Page,
    PageParams,
)

AR = TypeVar('AR')  # 聚合根类型
ID = TypeVar('ID')  # 主键类型


class ReadRepositoryProtocol(Protocol, Generic[AR, ID]):
    """
    领域读仓储接口：仅用于查询聚合根
    """

    async def get_by_id(self, id: ID) -> Optional[AR]:
        """按主键加载聚合根"""
        ...

    async def query_by_spec(self, spec: Specification[AR]) -> List[AR]:
        """按 Specification 查询聚合根列表"""
        ...

    async def query_one_by_spec(self, spec: Specification[AR]) -> Optional[AR]:
        """按 Specification 查询单个聚合根"""
        ...

    async def query_all_by_spec(self, spec: Specification[AR]) -> List[AR]:
        """按 Specification 查询所有满足条件的聚合根"""
        ...

    async def query_count_by_spec(self, spec: Specification[AR]) -> int:
        """统计满足过滤条件的聚合根数量"""
        ...

    async def query_exists_by_spec(self, spec: Specification[AR]) -> bool:
        """检查是否存在满足过滤条件的聚合根"""
        ...

    async def query_page_by_spec(
        self,
        spec: Specification[AR],
        page_params: PageParams,
        order_by: Optional[List[Any]] = None,
        projection: Optional[List[Any]] = None
    ) -> Page[AR]:
        """按 Specification 分页查询聚合根（新版，使用 PageParams）"""
        ...


class WriteRepositoryProtocol(Protocol, Generic[AR, ID]):
    """
    领域写仓储接口：仅用于修改聚合根
    """

    async def create(self, aggregate: AR) -> None:
        """新增聚合根"""
        ...

    async def update(self, aggregate: AR) -> None:
        """更新聚合根"""
        ...

    async def delete(self, aggregate: AR) -> None:
        """删除聚合根"""
        ...

    async def batch_create(self, aggregates: List[AR]) -> None:
        """批量新增聚合根"""
        ...

    async def batch_update(self, where_clause: Any, values: Dict[str, Any]) -> int:
        """批量更新聚合根"""
        ...

    async def batch_delete(self, aggregates: List[AR]) -> None:
        """批量删除聚合根"""
        ...


class RepositoryProtocol(
    ReadRepositoryProtocol[AR, ID],
    WriteRepositoryProtocol[AR, ID],
    Protocol,
    Generic[AR, ID]
):
    """
    聚合读写仓储接口：聚合根完整持久化操作契约
    """
    ...
