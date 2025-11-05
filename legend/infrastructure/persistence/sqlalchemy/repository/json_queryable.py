"""基础设施层JSON查询接口

将JSON查询处理完全下沉到基础设施层，保持领域层纯粹。
这些接口只在基础设施层内部使用，不暴露给领域层。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, TypeVar

from idp.framework.domain.repository import PageParams, PaginatedResult

# 泛型类型变量
T = TypeVar('T')  # 可以是PO或AR类型


class JsonQueryableRepository(Generic[T], ABC):
    """JSON查询仓储接口

    基础设施层专用接口，提供JSON DSL查询能力。
    这个接口不应该被领域层直接依赖。
    """

    @abstractmethod
    async def exists_by_json(self, json_spec: Dict[str, Any]) -> bool:
        """使用JSON规范检查实体是否存在

        Args:
            json_spec: JSON查询规范

        Returns:
            如果存在满足条件的实体则返回True，否则返回False
        """
        pass

    @abstractmethod
    async def query_by_json(self, json_spec: Dict[str, Any]) -> List[T]:
        """使用JSON规范查询实体

        Args:
            json_spec: JSON查询规范

        Returns:
            满足条件的实体列表
        """
        pass

    @abstractmethod
    async def find_page_by_json(
        self,
        json_spec: Dict[str, Any],
        page_params: PageParams
    ) -> PaginatedResult[T]:
        """使用JSON规范进行分页查询

        Args:
            json_spec: JSON查询规范
            page_params: 分页参数

        Returns:
            分页查询结果
        """
        pass

    @abstractmethod
    async def count_by_json(self, json_spec: Dict[str, Any]) -> int:
        """使用JSON规范统计实体数量

        Args:
            json_spec: JSON查询规范

        Returns:
            满足条件的实体数量
        """
        pass
