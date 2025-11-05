"""流式API的Specification服务

提供流式API的查询规范构建，具有：
- 链式调用
- 类型安全
- 可组合性
- 性能优化
- 业务语义化

设计原则：
- 流式API：支持链式调用
- 类型安全：完整的类型注解
- 可扩展：支持自定义扩展
- 高性能：智能缓存和池化
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from idp.framework.infrastructure.persistence.specification import (
    FilterOperator,
    Specification,
    SpecificationBuilder,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    SortDirection,
)

T = TypeVar('T')  # 实体类型


class FluentSpecificationBuilder(Generic[T]):
    """流式Specification构建器

    提供流式API的查询规范构建
    """

    def __init__(self, entity_type: type):
        self._builder = SpecificationBuilder()
        self._entity_type = entity_type

    # ============ 基础过滤方法 ============

    def filter(self, field: str, value: Any) -> 'FluentSpecificationBuilder[T]':
        """基础过滤"""
        self._builder.filter(field, value)
        return self

    def filter_by(self, field: str, operator: FilterOperator, value: Any) -> 'FluentSpecificationBuilder[T]':
        """指定操作符过滤"""
        self._builder.filter(field, operator, value)
        return self

    def where(self, field: str, operator: str, value: Any) -> 'FluentSpecificationBuilder[T]':
        """WHERE条件"""
        self._builder.where(field, operator, value)
        return self

    # ============ 高级过滤方法 ============

    def text_search(self, field: str, text: str) -> 'FluentSpecificationBuilder[T]':
        """文本搜索"""
        self._builder.text_search(field, text)
        return self

    def or_(self, *conditions) -> 'FluentSpecificationBuilder[T]':
        """OR条件"""
        self._builder.or_(*conditions)
        return self

    def and_(self, *conditions) -> 'FluentSpecificationBuilder[T]':
        """AND条件"""
        self._builder.and_(*conditions)
        return self

    def between(self, field: str, start: Any, end: Any) -> 'FluentSpecificationBuilder[T]':
        """范围查询"""
        self._builder.between(field, start, end)
        return self

    def in_(self, field: str, values: List[Any]) -> 'FluentSpecificationBuilder[T]':
        """IN查询"""
        self._builder.where(field, "in", values)
        return self

    # ============ 包含关系方法 ============

    def include(self, *relations: str) -> 'FluentSpecificationBuilder[T]':
        """包含关系"""
        self._builder.include(*relations)
        return self

    def select(self, *fields: str) -> 'FluentSpecificationBuilder[T]':
        """选择字段"""
        self._builder.select(*fields)
        return self

    # ============ 排序方法 ============

    def sort(self, field: str, direction: SortDirection = SortDirection.ASC) -> 'FluentSpecificationBuilder[T]':
        """排序"""
        self._builder.sort(field, direction)
        return self

    def sort_by(self, field: str, direction: str = "asc") -> 'FluentSpecificationBuilder[T]':
        """按字段排序"""
        sort_dir = SortDirection.ASC if direction.lower() == "asc" else SortDirection.DESC
        self._builder.sort(field, sort_dir)
        return self

    # ============ 分页方法 ============

    def page(self, offset: int, limit: int) -> 'FluentSpecificationBuilder[T]':
        """分页"""
        self._builder.set_page(page=offset // (limit or 1) + 1, size=limit)
        return self

    def limit(self, limit: int) -> 'FluentSpecificationBuilder[T]':
        """限制结果数量"""
        self._builder.set_page(page=0 // (limit or 1) + 1, size=limit)
        return self

    # ============ 统计方法 ============

    def count(self, field: str, alias: Optional[str] = None) -> 'FluentSpecificationBuilder[T]':
        """计数"""
        self._builder.count(field, alias)
        return self

    def sum(self, field: str, alias: Optional[str] = None) -> 'FluentSpecificationBuilder[T]':
        """求和"""
        self._builder.sum(field, alias)
        return self

    def avg(self, field: str, alias: Optional[str] = None) -> 'FluentSpecificationBuilder[T]':
        """平均值"""
        self._builder.avg(field, alias)
        return self

    def group_by(self, *fields: str) -> 'FluentSpecificationBuilder[T]':
        """分组"""
        self._builder.group_by(*fields)
        return self

    def having(self, field: str, operator: str, value: Any) -> 'FluentSpecificationBuilder[T]':
        """HAVING条件"""
        self._builder.having(field, operator, value)
        return self

    # ============ 构建方法 ============

    def build(self) -> Specification:
        """构建查询规范"""
        return self._builder.build()

    def to_json_spec(self) -> Dict[str, Any]:
        """转换为JSON规范"""
        return self._builder.to_json_spec()

    def reset(self) -> 'FluentSpecificationBuilder[T]':
        """重置构建器"""
        self._builder = SpecificationBuilder()
        return self


class BaseFluentSpecificationService(Generic[T], ABC):
    """基础流式Specification服务

    提供流式API的查询规范构建和管理功能
    """

    def __init__(self, entity_type: type):
        self._entity_type = entity_type
        self._builder_pool = []  # 构建器池

    def create_builder(self) -> FluentSpecificationBuilder[T]:
        """创建新的构建器实例"""
        if self._builder_pool:
            builder = self._builder_pool.pop()
            builder.reset()
            return builder
        return FluentSpecificationBuilder[T](self._entity_type)

    def return_builder(self, builder: FluentSpecificationBuilder[T]):
        """归还构建器到池中"""
        self._builder_pool.append(builder)

    @abstractmethod
    def get_default_includes(self) -> List[str]:
        """获取默认包含的关系"""
        pass

    @abstractmethod
    def get_default_sorts(self) -> List[tuple]:
        """获取默认排序"""
        pass

    # ============ 基础查询方法 ============

    def query(self) -> FluentSpecificationBuilder[T]:
        """开始查询构建"""
        builder = self.create_builder()

        # 应用默认包含
        for include in self.get_default_includes():
            builder.include(include)

        # 应用默认排序
        for field, direction in self.get_default_sorts():
            builder.sort_by(field, direction)

        return builder

    def find_by_id(self, entity_id: str) -> FluentSpecificationBuilder[T]:
        """根据ID查询"""
        return self.query().filter("id", entity_id)

    def find_by_field(self, field: str, value: Any) -> FluentSpecificationBuilder[T]:
        """根据字段查询"""
        return self.query().filter(field, value)

    def find_by_fields(self, **filters) -> FluentSpecificationBuilder[T]:
        """根据多个字段查询"""
        builder = self.query()
        for field, value in filters.items():
            if value is not None:
                builder.filter(field, value)
        return builder

    # ============ 搜索方法 ============

    def search(self, text: str, fields: Optional[List[str]] = None) -> FluentSpecificationBuilder[T]:
        """文本搜索"""
        builder = self.query()

        if not fields:
            fields = self.get_default_search_fields()

        if len(fields) == 1:
            builder.text_search(fields[0], text)
        else:
            builder.or_(*[
                lambda b, field=field: b.text_search(field, text)
                for field in fields
            ])

        return builder

    def advanced_search(
        self,
        text: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> FluentSpecificationBuilder[T]:
        """高级搜索"""
        builder = self.query()

        # 文本搜索
        if text:
            builder = self.search(text)

        # 过滤条件
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if isinstance(value, dict):
                        # 复杂条件
                        op = value.get("operator", "=")
                        val = value.get("value")
                        if val is not None:
                            builder.where(field, op, val)
                    else:
                        # 简单条件
                        builder.filter(field, value)

        return builder

    # ============ 预定义查询方法 ============

    def list_view(self) -> FluentSpecificationBuilder[T]:
        """列表视图"""
        return self.query()

    def detail_view(self, entity_id: str) -> FluentSpecificationBuilder[T]:
        """详情视图"""
        return self.query().filter("id", entity_id).include(*self.get_detail_includes())

    def summary_view(self) -> FluentSpecificationBuilder[T]:
        """摘要视图"""
        return self.query().select(*self.get_summary_fields())

    def pagination_view(self, offset: int = 0, limit: int = 20) -> FluentSpecificationBuilder[T]:
        """分页视图"""
        return self.query().page(offset, limit)

    # ============ 抽象方法 ============

    def get_default_search_fields(self) -> List[str]:
        """获取默认搜索字段"""
        return ["name", "code"]

    def get_detail_includes(self) -> List[str]:
        """获取详情视图包含的关系"""
        return self.get_default_includes()

    def get_summary_fields(self) -> List[str]:
        """获取摘要视图字段"""
        return ["id", "code", "name"]

    # ============ 缓存方法 ============

    @lru_cache(maxsize=64)
    def get_cached_spec(self, spec_key: str) -> Specification:
        """获取缓存的查询规范"""
        cache_specs = {
            "list_view": self.list_view().build(),
            "summary_view": self.summary_view().build(),
        }
        return cache_specs.get(spec_key, self.list_view().build())


class SpecificationFactory:
    """Specification工厂

    提供预定义的查询规范创建方法
    """

    @staticmethod
    def create_list_spec(
        includes: Optional[List[str]] = None,
        sorts: Optional[List[tuple]] = None,
        page: Optional[Dict[str, int]] = None
    ) -> Specification:
        """创建列表查询规范"""
        builder = SpecificationBuilder()

        if includes:
            for include in includes:
                builder.include(include)

        if sorts:
            for field, direction in sorts:
                builder.add_sort(field, direction)

        if page:
            builder.set_page(page=page.get('offset', 0) //
                             (page.get('limit') or 1) + 1, size=page.get('limit'))

        return builder.build()

    @staticmethod
    def create_detail_spec(
        entity_id: str,
        includes: Optional[List[str]] = None
    ) -> Specification:
        """创建详情查询规范"""
        builder = SpecificationBuilder()
        builder.by_id(entity_id)

        if includes:
            for include in includes:
                builder.include(include)

        return builder.build()

    @staticmethod
    def create_search_spec(
        search_text: str,
        search_fields: List[str],
        includes: Optional[List[str]] = None
    ) -> Specification:
        """创建搜索查询规范"""
        builder = SpecificationBuilder()

        # 文本搜索
        if len(search_fields) == 1:
            builder.text_search(search_fields[0], search_text)
        else:
            builder.or_(*[
                lambda b, field=field: b.text_search(field, search_text)
                for field in search_fields
            ])

        if includes:
            for include in includes:
                builder.include(include)

        return builder.build()


# ============ 使用示例 ============
"""
# 1. 基础查询
service = WarehouseFluentSpecificationService()
spec = service.query().filter("tenant_id", "tenant123").build()

# 2. 链式查询
spec = (service.query()
        .filter("tenant_id", "tenant123")
        .filter("is_operational", True)
        .include("zones")
        .sort_by("name", "asc")
        .page(0, 20)
        .build())

# 3. 搜索查询
spec = service.search("warehouse", ["name", "code"]).build()

# 4. 高级搜索
spec = (service.advanced_search(
    text="warehouse",
    filters={"is_operational": True, "warehouse_type": "distribution"}
)
.include("zones", "warehouse_type")
.sort_by("created_at", "desc")
.build())

# 5. 预定义查询
spec = service.list_view().build()
spec = service.detail_view("warehouse123").build()
spec = service.summary_view().build()
spec = service.pagination_view(0, 20).build()
"""
