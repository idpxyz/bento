# 规范模式(Specification Pattern)特性文档

本文档详细说明了规范模式实现的核心特性和代码示例。

## 1. 核心接口设计

```python
class Specification(Generic[T], ABC):
    """基础规范接口"""
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        pass

    @abstractmethod
    def to_query_params(self) -> Dict[str, Any]:
        pass
```

特点：
- 使用泛型参数T支持类型安全
- 提供两个核心方法：对象匹配和查询参数转换
- 采用抽象基类确保接口实现

## 2. 构建器体系

```python
class SpecificationBuilder(Generic[T]):
    """基础构建器"""
    def __init__(self):
        self.criteria: List[Criterion] = []
        self.sorts: List[Sort] = []
        self.page: Optional[Page] = None
        self.selected_fields: List[str] = []
        self.included_relations: List[str] = []
        self.statistics: List[Statistic] = []
        self.group_by_fields: List[str] = []
        self.having_conditions: List[Having] = []
        self.filter_groups: List[FilterGroup] = []
```

特点：
- 统一管理查询条件
- 支持多种查询特性
- 状态管理清晰

## 3. 条件系统设计

```python
# 基础条件接口
class Criterion(ABC):
    @abstractmethod
    def to_filter(self) -> Filter:
        pass

# 比较条件
class ComparisonCriterion(Criterion):
    def __init__(self, field: str, value: Any, operator: FilterOperator):
        self.field = field
        self.value = value
        self.operator = operator

# 逻辑条件
class AndCriterion(CompositeCriterion):
    def __init__(self, criteria: List[Criterion]):
        super().__init__(criteria, LogicalOperator.AND)
```

特点：
- 条件类型可扩展
- 支持复杂的逻辑组合
- 清晰的类型层次

## 4. 查询构建示例

```python
# 基础查询
spec = (SpecificationBuilder()
    .filter("status", "active")
    .between("age", 18, 65)
    .build())

# 复杂逻辑查询
spec = (SpecificationBuilder()
    .and_(
        lambda b: b.by_id(user_id),
        lambda b: b.or_(
            lambda b: b.text_search("name", "John"),
            lambda b: b.text_search("email", "john@example.com")
        )
    )
    .build())
```

特点：
- 链式调用API
- 支持lambda表达式
- 直观的查询构建

## 5. 特殊查询支持

```python
# JSON操作
spec = (SpecificationBuilder()
    .json_contains("metadata", {"verified": True})
    .json_has_key("settings", "theme")
    .build())

# 统计查询
spec = (SpecificationBuilder()
    .count("id", "total_users")
    .avg("score", "average_score")
    .group_by("department")
    .having("count", ">", 5)
    .build())
```

特点：
- 支持复杂数据类型
- 支持高级统计操作
- 灵活的查询组合

## 6. 领域特定构建器

```python
class EntitySpecificationBuilder(SpecificationBuilder[T]):
    """实体查询构建器"""
    def by_status(self, status: str) -> 'EntitySpecificationBuilder[T]':
        return self.add_criterion(EqualsCriterion('status', status))
    
    def is_active(self, active: bool = True) -> 'EntitySpecificationBuilder[T]':
        return self.add_criterion(EqualsCriterion('is_active', active))

class AggregateSpecificationBuilder(EntitySpecificationBuilder[T]):
    """聚合根查询构建器"""
    def by_version(self, version: int) -> 'AggregateSpecificationBuilder[T]':
        return self.add_criterion(EqualsCriterion('version', version))
```

特点：
- 领域特定的查询方法
- 继承体系清晰
- 类型安全的方法链

## 7. 扩展性示例

```python
# 添加新的条件类型
class NewCriterion(Criterion):
    def __init__(self, field: str, value: Any):
        self.field = field
        self.value = value
    
    def to_filter(self) -> Filter:
        return Filter(
            field=self.field,
            operator=FilterOperator.NEW_OP,
            value=self.value
        )

# 扩展构建器
class CustomSpecificationBuilder(EntitySpecificationBuilder[T]):
    def custom_query(self, param: str) -> 'CustomSpecificationBuilder[T]':
        return self.add_criterion(CustomCriterion('field', param))
```

特点：
- 易于扩展新功能
- 保持类型安全
- 维护代码一致性

## 8. 性能优化支持

```python
spec = (SpecificationBuilder()
    .select("id", "name", "email")  # 字段选择
    .include("profile", "orders.items")  # 关联加载
    .set_page(offset=0, limit=10)  # 分页
    .add_sort("created_at", ascending=False)  # 排序
    .build())
```

特点：
- 精确的数据加载
- 性能优化选项
- 灵活的查询控制

## 9. 错误处理

```python
def set_page(self, offset: Optional[int] = None, limit: Optional[int] = None):
    if offset is not None and offset < 0:
        raise ValueError("Page offset cannot be negative")
    if limit is not None and limit < 0:
        raise ValueError("Page limit cannot be negative")
    self.page = Page(offset=offset, limit=limit)
    return self
```

特点：
- 严格的参数验证
- 清晰的错误信息
- 类型安全检查

## 10. 实际应用示例

```python
# 用户查询示例
def find_active_users_by_department(department: str) -> List[User]:
    spec = (EntitySpecificationBuilder[User]()
        .is_active()
        .by_status("employed")
        .filter("department", department)
        .select("id", "name", "email", "department")
        .include("profile")
        .add_sort("name")
        .set_page(limit=100)
        .build())
    
    return user_repository.find_by_spec(spec)
```

特点：
- 实际业务场景应用
- 代码可读性好
- 维护性强

## 11. 总结

这个规范模式的实现具有以下核心优势：

1. **设计优势**
   - 采用DDD原则
   - 类型安全
   - 模块化设计
   - 可扩展架构

2. **功能优势**
   - 丰富的查询能力
   - 灵活的条件组合
   - 完善的性能优化
   - 强大的扩展性

3. **实践优势**
   - 易于使用
   - 易于维护
   - 易于测试
   - 易于扩展

4. **技术优势**
   - Python类型系统支持
   - 清晰的接口设计
   - 完善的错误处理
   - 优秀的代码组织

这个实现不仅提供了强大的查询能力，还确保了代码的可维护性和可扩展性。通过类型系统和接口设计，它能够有效地支持复杂的业务查询需求，同时保持代码的清晰和可控。
