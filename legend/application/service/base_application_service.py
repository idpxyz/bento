"""基础应用服务

提供应用服务的通用基类，负责协调QueryService和数据转换，
简化具体聚合应用服务的实现。

职责：
- 协调查询服务和数据转换
- 提供统一的响应构建模式
- 封装常用的用例编排逻辑
- 作为API层和领域层之间的桥梁

设计理念：
- 用例编排器：专注业务流程协调
- 数据转换隔离：统一的转换入口
- 响应构建标准化：一致的API响应格式
- 类型安全：基于泛型的强类型支持
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from idp.framework.domain.repository import PageParams

# 类型变量定义
TDTO = TypeVar('TDTO')  # 领域DTO类型
TResponse = TypeVar('TResponse')  # API响应类型
TPaginatedResponse = TypeVar('TPaginatedResponse')  # 分页响应类型
TQueryService = TypeVar('TQueryService')  # 查询服务类型


class BaseApplicationService(Generic[TDTO, TResponse, TPaginatedResponse, TQueryService], ABC):
    """基础应用服务类

    提供通用的应用服务模式，具体的聚合应用服务可以继承此类。

    类型参数:
        TDTO: 领域数据传输对象类型
        TResponse: API响应对象类型  
        TPaginatedResponse: 分页响应对象类型
        TQueryService: 查询服务类型

    职责:
        1. 协调查询服务和数据转换
        2. 提供统一的响应构建模式
        3. 封装常用的用例编排逻辑
        4. 保持API层与领域层的隔离

    使用示例:
        ```python
        class ProductApplicationService(
            BaseApplicationService[
                ProductDTO, 
                ProductResponse, 
                PaginatedProductResponse,
                ProductQueryService
            ]
        ):
            def dto_to_response(self, dto: ProductDTO) -> ProductResponse:
                return product_converter.to_response(dto)

            def build_paginated_response(self, items, total, page_params):
                return PaginatedProductResponse(...)
        ```
    """

    def __init__(self, query_service: TQueryService):
        """初始化基础应用服务

        Args:
            query_service: 查询服务实例
        """
        self._query_service = query_service

    @abstractmethod
    def dto_to_response(self, dto: TDTO) -> TResponse:
        """将DTO转换为响应对象

        Args:
            dto: 领域数据传输对象

        Returns:
            API响应对象

        Note:
            子类必须实现此方法，定义具体的转换逻辑
        """
        pass

    @abstractmethod
    def dto_list_to_response_list(self, dtos: List[TDTO]) -> List[TResponse]:
        """将DTO列表转换为响应对象列表

        Args:
            dtos: 领域数据传输对象列表

        Returns:
            API响应对象列表

        Note:
            子类必须实现此方法，通常可以通过循环调用dto_to_response实现
        """
        pass

    @abstractmethod
    def build_paginated_response(
        self,
        items: List[TResponse],
        total: int,
        page_params: PageParams
    ) -> TPaginatedResponse:
        """构建分页响应对象

        Args:
            items: 响应对象列表
            total: 总记录数
            page_params: 分页参数

        Returns:
            分页响应对象

        Note:
            子类必须实现此方法，定义具体的分页响应构建逻辑
        """
        pass

    # ============ 通用查询方法 ============

    async def get_by_id(self, entity_id: str) -> Optional[TResponse]:
        """根据ID获取单个实体

        Args:
            entity_id: 实体ID

        Returns:
            响应对象或None
        """
        dto = await self._query_service.get_by_id(entity_id)
        if not dto:
            return None
        return self.dto_to_response(dto)

    async def query_by_json_spec(
        self,
        json_spec: dict,
        page_params: PageParams
    ) -> TPaginatedResponse:
        """基于 JSON 规范分页查询

        Args:
            json_spec: JSON查询规范
            page_params: 分页参数

        Returns:
            分页响应对象
        """
        # 1. 调用查询服务获取领域DTO
        page_result = await self._query_service.query_by_json_spec(
            json_spec=json_spec,
            page_params=page_params
        )

        # 2. 转换为响应对象
        response_items = self.dto_list_to_response_list(page_result.items)

        # 3. 构建分页响应
        return self.build_paginated_response(
            items=response_items,
            total=page_result.total,
            page_params=page_params
        )

    async def search_by_json_spec(self, json_spec: dict) -> List[TResponse]:
        """基于 JSON 规范搜索（无分页）

        Args:
            json_spec: JSON查询规范

        Returns:
            响应对象列表
        """
        # 1. 调用查询服务获取领域DTO
        dtos = await self._query_service.search_by_json_spec(json_spec=json_spec)

        # 2. 转换为响应对象
        return self.dto_list_to_response_list(dtos)

    async def count_by_json_spec(self, json_spec: dict) -> int:
        """基于 JSON 规范统计数量

        Args:
            json_spec: JSON查询规范

        Returns:
            实体数量
        """
        return await self._query_service.count_by_json_spec(json_spec=json_spec)

    async def exists_by_json_spec(self, json_spec: dict) -> bool:
        """基于 JSON 规范检查是否存在

        Args:
            json_spec: JSON查询规范

        Returns:
            是否存在匹配的实体
        """
        return await self._query_service.exists_by_json_spec(json_spec=json_spec)

    # ============ 便捷查询方法 ============

    async def find_by_code_pattern(self, pattern: str) -> List[TResponse]:
        """根据代码模式查找

        Args:
            pattern: 代码模式

        Returns:
            匹配的响应对象列表
        """
        dtos = await self._query_service.find_by_code_pattern(pattern)
        return self.dto_list_to_response_list(dtos)

    async def find_by_name_pattern(self, pattern: str) -> List[TResponse]:
        """根据名称模式查找

        Args:
            pattern: 名称模式

        Returns:
            匹配的响应对象列表
        """
        dtos = await self._query_service.find_by_name_pattern(pattern)
        return self.dto_list_to_response_list(dtos)

    async def find_active(self, additional_filters: Optional[List[dict]] = None) -> List[TResponse]:
        """查找活跃的实体

        Args:
            additional_filters: 额外的过滤条件

        Returns:
            活跃实体响应对象列表
        """
        dtos = await self._query_service.find_active(additional_filters)
        return self.dto_list_to_response_list(dtos)

    # ============ 扩展点方法 ============

    def build_search_spec(self, **kwargs) -> dict:
        """构建搜索规范

        Args:
            **kwargs: 搜索参数

        Returns:
            JSON查询规范

        Note:
            子类可以重写此方法来定义特定的搜索逻辑
        """
        return {"filters": []}

    async def search_by_keyword(
        self,
        keyword: str,
        additional_filters: Optional[List[dict]] = None
    ) -> List[TResponse]:
        """关键词搜索

        默认在 code, name, description 字段中搜索。
        子类可以重写此方法来定义特定的搜索逻辑。

        Args:
            keyword: 搜索关键词
            additional_filters: 额外的过滤条件

        Returns:
            匹配的响应对象列表
        """
        filters = [
            {
                "operator": "or",
                "conditions": [
                    {"field": "code", "operator": "contains", "value": keyword},
                    {"field": "name", "operator": "contains", "value": keyword},
                    {"field": "description", "operator": "contains", "value": keyword}
                ]
            }
        ]

        if additional_filters:
            filters.extend(additional_filters)

        spec = {"filters": filters}
        return await self.search_by_json_spec(spec)

    # ============ 业务用例编排方法 ============

    async def list_all_with_filters(self, **filter_params) -> List[TResponse]:
        """根据过滤参数列出所有实体

        Args:
            **filter_params: 过滤参数

        Returns:
            响应对象列表

        Note:
            子类可以重写build_search_spec方法来定义具体的过滤逻辑
        """
        spec = self.build_search_spec(**filter_params)
        return await self.search_by_json_spec(spec)

    async def get_summary_stats(self, json_spec: Optional[dict] = None) -> dict:
        """获取汇总统计信息

        Args:
            json_spec: 可选的查询规范

        Returns:
            统计信息字典
        """
        if json_spec is None:
            json_spec = {}

        total_count = await self.count_by_json_spec(json_spec)

        return {
            "total_count": total_count,
            "has_data": total_count > 0
        }


class BaseAggregateApplicationService(BaseApplicationService[TDTO, TResponse, TPaginatedResponse, TQueryService]):
    """聚合根应用服务基类

    为聚合根提供额外的便捷方法，如软删除查询等。
    """

    async def find_not_deleted(self, additional_filters: Optional[List[dict]] = None) -> List[TResponse]:
        """查找未删除的实体（适用于软删除）

        Args:
            additional_filters: 额外的过滤条件

        Returns:
            未删除实体响应对象列表
        """
        dtos = await self._query_service.find_not_deleted(additional_filters)
        return self.dto_list_to_response_list(dtos)

    async def find_by_version(self, version: int) -> List[TResponse]:
        """根据版本号查找实体

        Args:
            version: 版本号

        Returns:
            匹配版本的实体响应对象列表
        """
        dtos = await self._query_service.find_by_version(version)
        return self.dto_list_to_response_list(dtos)
