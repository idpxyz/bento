"""通用搜索功能Mixin

提供标准的搜索模式，减少重复代码：
- 多字段文本搜索
- 关联字段过滤
- 详情级过滤
- 应用层过滤组合

重构说明：
- 移除与BaseApplicationService冲突的抽象方法
- 改为使用扩展点模式，依赖基类实现
- 专注高级搜索功能，避免基础功能重复
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')  # DTO类型


@dataclass
class SearchField:
    """搜索字段配置"""
    field_name: str
    search_method: str = "contains"  # contains, exact, starts_with, pattern
    case_sensitive: bool = False


@dataclass
class FilterConfig:
    """过滤配置"""
    field_path: str  # 支持嵌套字段 "details.scope_level"
    filter_type: str = "equals"  # equals, in, contains, between
    create_filtered_dto: bool = False  # 是否需要创建过滤后的DTO


class SearchMixin(Generic[T], ABC):
    """通用搜索功能Mixin - 重构版本

    专注高级搜索功能，避免与基类功能重复。
    依赖BaseApplicationService的基础查询方法。

    使用方法：
    ```python
    class OptionCategoryApplicationService(BaseApplicationService, SearchMixin[OptionCategoryDTO]):
        def get_search_fields(self) -> List[SearchField]:
            return [
                SearchField("code", "contains"),
                SearchField("name", "contains"), 
                SearchField("description", "contains")
            ]

        def get_filter_configs(self) -> Dict[str, FilterConfig]:
            return {
                "scope_levels": FilterConfig("details.scope_level", "in", True),
                "tenant_id": FilterConfig("details.tenant_id", "equals", True),
                "has_details": FilterConfig("details", "has_items")
            }
    ```
    """

    @abstractmethod
    def get_search_fields(self) -> List[SearchField]:
        """返回可搜索的字段配置"""
        pass

    @abstractmethod
    def get_filter_configs(self) -> Dict[str, FilterConfig]:
        """返回过滤器配置"""
        pass

    @abstractmethod
    def create_filtered_dto(self, original: T, filtered_data: Dict[str, Any]) -> T:
        """创建过滤后的DTO（用于详情级过滤）"""
        pass

    # 扩展点：依赖基类实现，而不是重复定义
    async def _get_base_list_all(self) -> List[T]:
        """获取所有记录 - 委托给基类实现"""
        # 子类需要实现此方法，调用基类的list_all或search_by_json_spec
        raise NotImplementedError("子类必须实现此方法，调用基类的查询方法")

    async def _get_base_find_by_code_pattern(self, pattern: str) -> List[T]:
        """按代码模式查找 - 委托给基类实现"""
        # 子类需要实现此方法，调用基类的find_by_code_pattern
        raise NotImplementedError("子类必须实现此方法，调用基类的查询方法")

    async def _get_base_find_by_name_pattern(self, pattern: str) -> List[T]:
        """按名称模式查找 - 委托给基类实现"""
        # 子类需要实现此方法，调用基类的find_by_name_pattern
        raise NotImplementedError("子类必须实现此方法，调用基类的查询方法")

    async def universal_search(
        self,
        search_text: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[T]:
        """通用搜索实现

        Args:
            search_text: 搜索文本，会在所有配置的字段中搜索
            filters: 过滤条件字典
            limit: 结果数量限制

        Returns:
            匹配的DTO列表
        """
        results = []
        filters = filters or {}

        # 1. 文本搜索
        if search_text:
            all_found = {}

            # 基于配置的字段搜索
            search_fields = self.get_search_fields()
            for field_config in search_fields:
                if field_config.field_name == "code":
                    field_results = await self._get_base_find_by_code_pattern(search_text)
                elif field_config.field_name == "name":
                    field_results = await self._get_base_find_by_name_pattern(search_text)
                elif field_config.field_name == "description":
                    # 描述搜索的通用实现
                    field_results = await self._search_description_field(search_text)
                else:
                    # 其他字段的通用搜索
                    field_results = await self._search_generic_field(
                        field_config.field_name,
                        search_text,
                        field_config
                    )

                for result in field_results:
                    all_found[self._get_id(result)] = result

            results = list(all_found.values())
        else:
            results = await self._get_base_list_all()

        # 2. 应用过滤器
        filter_configs = self.get_filter_configs()
        for filter_name, filter_value in filters.items():
            if filter_value is None:
                continue

            if filter_name not in filter_configs:
                continue

            config = filter_configs[filter_name]
            results = await self._apply_filter(results, config, filter_value)

        # 3. 应用limit
        if limit:
            results = results[:limit]

        return results

    async def _search_description_field(self, search_text: str) -> List[T]:
        """描述字段的通用搜索实现"""
        all_items = await self._get_base_list_all()
        results = []

        for item in all_items:
            description = self._get_field_value(item, "description")
            if (description and
                    search_text.upper() in description.upper()):
                results.append(item)

        return results

    async def _search_generic_field(
        self,
        field_name: str,
        search_text: str,
        config: SearchField
    ) -> List[T]:
        """通用字段搜索实现"""
        all_items = await self._get_base_list_all()
        results = []

        for item in all_items:
            field_value = self._get_field_value(item, field_name)
            if field_value and self._matches_search(field_value, search_text, config):
                results.append(item)

        return results

    def _matches_search(self, field_value: Any, search_text: str, config: SearchField) -> bool:
        """检查字段值是否匹配搜索条件"""
        if not field_value:
            return False

        field_str = str(field_value)
        if not config.case_sensitive:
            field_str = field_str.upper()
            search_text = search_text.upper()

        if config.search_method == "contains":
            return search_text in field_str
        elif config.search_method == "exact":
            return field_str == search_text
        elif config.search_method == "starts_with":
            return field_str.startswith(search_text)
        else:
            return search_text in field_str

    async def _apply_filter(self, results: List[T], config: FilterConfig, filter_value: Any) -> List[T]:
        """应用单个过滤器"""
        if config.create_filtered_dto:
            # 需要详情级过滤，创建新的DTO
            return await self._apply_detail_filter(results, config, filter_value)
        else:
            # 分类级过滤
            return await self._apply_category_filter(results, config, filter_value)

    async def _apply_detail_filter(self, results: List[T], config: FilterConfig, filter_value: Any) -> List[T]:
        """应用详情级过滤"""
        filtered_results = []

        for result in results:
            filtered_details = []
            details = self._get_field_value(result, "details") or []

            for detail in details:
                detail_field_value = self._get_nested_field_value(
                    detail, config.field_path)
                if self._matches_filter(detail_field_value, filter_value, config.filter_type):
                    filtered_details.append(detail)

            if filtered_details:
                # 创建包含过滤详情的新DTO
                filtered_dto = self.create_filtered_dto(
                    result, {"details": filtered_details})
                filtered_results.append(filtered_dto)

        return filtered_results

    async def _apply_category_filter(self, results: List[T], config: FilterConfig, filter_value: Any) -> List[T]:
        """应用分类级过滤"""
        filtered_results = []

        for result in results:
            field_value = self._get_nested_field_value(
                result, config.field_path)
            if self._matches_filter(field_value, filter_value, config.filter_type):
                filtered_results.append(result)

        return filtered_results

    def _matches_filter(self, field_value: Any, filter_value: Any, filter_type: str) -> bool:
        """检查字段值是否匹配过滤条件"""
        if field_value is None:
            return False

        if filter_type == "equals":
            return field_value == filter_value
        elif filter_type == "in":
            return field_value in filter_value if isinstance(filter_value, (list, tuple)) else field_value == filter_value
        elif filter_type == "contains":
            return str(filter_value).lower() in str(field_value).lower()
        elif filter_type == "between":
            if isinstance(filter_value, (list, tuple)) and len(filter_value) == 2:
                return filter_value[0] <= field_value <= filter_value[1]
            return False
        elif filter_type == "has_items":
            return bool(field_value) if isinstance(field_value, (list, tuple)) else bool(field_value)
        else:
            return field_value == filter_value

    def _get_field_value(self, obj: Any, field_name: str) -> Any:
        """获取对象的字段值"""
        return getattr(obj, field_name, None)

    def _get_nested_field_value(self, obj: Any, field_path: str) -> Any:
        """获取嵌套字段值"""
        current = obj
        for part in field_path.split('.'):
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current

    def _get_id(self, obj: Any) -> str:
        """获取对象的ID"""
        return getattr(obj, 'id', str(id(obj)))
