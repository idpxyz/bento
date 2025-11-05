# 规范模式(Specification Pattern)开发文档

## 1. 概述

规范模式是一种领域驱动设计(DDD)中的模式，用于封装复杂的查询逻辑。本实现提供了一个灵活、类型安全且可扩展的查询构建系统。

### 1.1 主要特性

- 类型安全的查询构建
- 链式方法调用API
- 支持复杂的逻辑组合(AND, OR, NOT)
- 丰富的查询操作符
- 分页和排序支持
- 字段选择和关联加载
- 统计查询支持
- 支持JSON和数组操作
- 支持时间范围查询

### 1.2 核心组件

- 基础规范接口和实现
- 规范构建器
- 查询条件(Criteria)
- 过滤器和操作符
- 分页和排序

## 2. 架构设计

### 2.1 核心接口

```python
class Specification(Generic[T], ABC):
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        pass

    @abstractmethod
    def to_query_params(self) -> Dict[str, Any]:
        pass
```

### 2.2 主要组件

1. **规范(Specification)**
   - `Specification`: 基础规范接口
   - `CompositeSpecification`: 组合规范实现

2. **构建器(Builder)**
   - `SpecificationBuilder`: 基础构建器
   - `EntitySpecificationBuilder`: 实体查询构建器
   - `AggregateSpecificationBuilder`: 聚合根查询构建器

3. **条件(Criteria)**
   - 比较条件: `ComparisonCriterion`, `EqualsCriterion` 等
   - 逻辑条件: `AndCriterion`, `OrCriterion`, `NotCriterion`
   - 时间条件: `DateRangeCriterion`, `RelativeDateCriterion`

4. **操作符(Operators)**
   - `FilterOperator`: 过滤操作符
   - `LogicalOperator`: 逻辑操作符
   - `StatisticalFunction`: 统计函数

## 3. 使用指南

### 3.1 基础查询

```python
# 简单等值查询
spec = (SpecificationBuilder()
    .filter("status", "active")
    .build())

# 范围查询
spec = (SpecificationBuilder()
    .between("age", 18, 65)
    .build())

# 文本搜索
spec = (SpecificationBuilder()
    .text_search("name", "John", case_sensitive=False)
    .build())
```

### 3.2 复杂逻辑查询

```python
# AND/OR组合
spec = (SpecificationBuilder()
    .and_(
        lambda b: b.by_id(user_id),
        lambda b: b.or_(
            lambda b: b.text_search("name", "John"),
            lambda b: b.text_search("email", "john@example.com")
        )
    )
    .build())

# 过滤组
spec = (SpecificationBuilder()
    .group("or")
    .where("status", "=", "active")
    .where("status", "=", "pending")
    .end_group()
    .build())
```

### 3.3 高级特性

```python
# 字段选择和关联加载
spec = (SpecificationBuilder()
    .select("id", "name", "email")
    .include("profile", "orders.items")
    .build())

# 统计查询
spec = (SpecificationBuilder()
    .count("id", "total_users")
    .avg("score", "average_score")
    .group_by("department")
    .having("count", ">", 5)
    .build())

# JSON操作
spec = (SpecificationBuilder()
    .json_contains("metadata", {"verified": True})
    .json_has_key("settings", "theme")
    .build())
```

## 4. 最佳实践

### 4.1 查询构建

1. 使用链式调用构建查询
2. 优先使用类型安全的方法
3. 合理组织复杂查询的逻辑结构
4. 使用适当的构建器子类

### 4.2 性能优化

1. 合理使用字段选择(select)
2. 按需加载关联(include)
3. 使用分页控制结果集大小
4. 优化统计查询的分组和条件

### 4.3 代码组织

1. 将常用查询封装为命名方法
2. 使用领域特定的构建器扩展
3. 保持查询逻辑的可重用性
4. 遵循DDD原则组织代码

## 5. 扩展开发

### 5.1 添加新的条件类型

1. 创建新的Criterion类
2. 实现to_filter方法
3. 在SpecificationBuilder中添加构建方法

```python
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
```

### 5.2 扩展构建器

1. 继承现有构建器类
2. 添加领域特定的查询方法
3. 重用基础构建块

```python
class CustomSpecificationBuilder(EntitySpecificationBuilder[T]):
    def custom_query(self, param: str) -> 'CustomSpecificationBuilder[T]':
        return self.add_criterion(CustomCriterion('field', param))
```

## 6. 测试策略

### 6.1 单元测试

1. 测试各种条件类型
2. 测试逻辑组合
3. 测试边界条件
4. 测试错误处理

### 6.2 集成测试

1. 测试与数据库的集成
2. 测试复杂查询场景
3. 测试性能和优化

## 7. 维护和更新

### 7.1 版本控制

1. 遵循语义化版本
2. 维护更新日志
3. 文档同步更新

### 7.2 性能监控

1. 监控查询执行时间
2. 分析查询计划
3. 优化常见查询模式

## 8. 常见问题

### 8.1 查询优化

Q: 如何优化复杂查询的性能？
A: 
- 使用适当的索引
- 限制关联加载深度
- 使用字段选择减少数据传输
- 合理使用分页

### 8.2 扩展性

Q: 如何添加自定义查询操作符？
A:
1. 在FilterOperator中添加新的操作符
2. 创建对应的Criterion类
3. 在SpecificationBuilder中添加构建方法

### 8.3 最佳实践

Q: 如何组织大型项目中的查询逻辑？
A:
1. 创建领域特定的构建器
2. 封装常用查询模式
3. 使用命名约定保持一致性
4. 保持文档的同步更新

## 9. 未来规划

### 9.1 功能增强

1. 支持更多数据类型和操作符
2. 增强统计查询能力
3. 改进性能优化策略

### 9.2 工具支持

1. 开发查询构建器UI
2. 提供查询分析工具
3. 增加性能监控功能

## 10. 参考资料

1. Domain-Driven Design (Eric Evans)
2. Specification Pattern (Martin Fowler)
3. FastAPI Documentation
4. SQLAlchemy Documentation

## 11. 变更日志

### v1.0.0 (2024-02-28)

- 初始版本
- 实现基础规范模式
- 支持复杂查询构建
- 添加实体和聚合根支持