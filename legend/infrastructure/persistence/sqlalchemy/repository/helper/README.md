# Repository Helper 模块

本模块提供了 SQLAlchemy 仓储层的辅助工具，包括查询构建、字段解析、安全校验、分页限制等功能。

## 核心组件

### 1. QueryBuilder

查询构建器，用于构建 SQLAlchemy 查询语句。

**特性：**
- 支持过滤、排序、分页、字段选择、预加载等操作
- 集成字段安全校验功能
- 支持显式 join 声明和去重
- 支持统计函数和分组查询
- **分页和查询限制功能**：防止恶意查询，保护系统性能

**使用示例：**
```python
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.query_builder import QueryBuilder
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import FieldResolver

# 创建字段解析器（带安全配置）
field_resolver = FieldResolver(UserPO, security_config)
query_builder = QueryBuilder(UserPO, field_resolver)

# 构建查询
query = query_builder.reset()\
    .apply_filters(filters)\
    .apply_sorts(sorts)\
    .apply_pagination(page)\
    .apply_field_selection(fields)\
    .build()
```

### 2. FieldResolver

字段解析器，负责将字段路径解析为 SQLAlchemy 列对象，并提供安全校验功能。

**特性：**
- 支持嵌套字段路径解析（如 `user.department.name`）
- 集成字段安全校验
- 支持白名单/黑名单控制
- 支持基于权限的访问控制
- 支持关系字段安全

**使用示例：**
```python
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
    FieldResolver, FieldSecurityConfig
)

# 创建安全配置
security_config = FieldSecurityConfig(
    allowed_fields={"id", "username", "email", "department"},
    forbidden_fields={"password_hash", "salary"},
    field_permissions={
        "phone": "filter",  # 需要 filter 权限
        "salary": "admin"   # 需要 admin 权限
    }
)

# 创建字段解析器
resolver = FieldResolver(UserPO, security_config)

# 解析字段（带安全验证）
try:
    field = resolver.resolve("username", operation="read")
    print("✓ 允许访问")
except FieldSecurityError as e:
    print(f"✗ 访问被拒绝: {e}")
```

### 3. JsonSpecParser

JSON 规范解析器，将 JSON 格式的查询规范转换为 Specification 对象。

**特性：**
- 支持完整的查询规范解析
- 集成字段安全校验
- 自动去重过滤条件
- 支持统计函数和分组查询

**使用示例：**
```python
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.json_spec_parser import JsonSpecParser

# 创建解析器（带安全配置）
parser = JsonSpecParser(UserPO, field_resolver)

# 解析 JSON 规范
json_spec = {
    "filters": [
        {"field": "username", "operator": "like", "value": "john%"}
    ],
    "sorts": [
        {"field": "created_at", "direction": "desc"}
    ],
    "page": {"offset": 0, "limit": 10},
    "fields": ["id", "username", "email"]
}

spec = parser.parse(json_spec)
```

## 分页和查询限制功能

### 概述

分页和查询限制功能提供了强大的查询控制能力，支持多种分页方式，并内置性能保护机制，防止恶意查询对系统造成性能影响。

### 核心特性

1. **多种分页方式**
   - 页码分页：使用 page/size 参数
   - 偏移量分页：使用 offset/limit 参数
   - 游标分页：适用于大数据量场景
   - 智能分页：自动处理边界情况

2. **性能保护**
   - 查询限制：防止返回过多结果
   - 偏移量限制：防止深度分页性能问题
   - 参数验证：自动修正无效参数
   - 默认限制：确保查询性能

3. **可配置性**
   - 灵活配置：支持自定义各种限制参数
   - 环境适配：可根据不同环境调整限制
   - 安全策略：支持不同安全级别的配置

### 使用场景

#### 1. 基本分页
```python
from dataclasses import dataclass

@dataclass
class PageParams:
    page: int = 1
    size: int = 20

# 创建分页参数
page_params = PageParams(page=2, size=10)

# 应用分页
query_builder.apply_pagination(page_params)
```

#### 2. 智能分页
```python
# 自动处理边界情况
query_builder.apply_smart_pagination(
    page_num=2,      # 页码
    page_size=15,    # 页面大小
    max_pages=100    # 最大页码限制（可选）
)
```

#### 3. 查询限制配置
```python
# 设置自定义查询限制
query_builder.set_query_limits(
    max_limit=500,        # 最大查询限制
    default_limit=25,     # 默认查询限制
    max_offset=5000,      # 最大偏移量
    max_page_size=50,     # 最大页面大小
    default_page_size=10  # 默认页面大小
)
```

#### 4. 分页信息获取
```python
# 获取完整的分页信息
pagination_info = query_builder.get_pagination_info(
    page_num=3,
    page_size=20,
    total_count=100
)

# 返回信息包含：
{
    'page_num': 3,           # 当前页码
    'page_size': 20,         # 页面大小
    'total_count': 100,      # 总记录数
    'total_pages': 5,        # 总页数
    'offset': 40,            # 当前偏移量
    'has_next': True,        # 是否有下一页
    'has_prev': True,        # 是否有上一页
    'start_index': 41,       # 当前页起始索引
    'end_index': 60          # 当前页结束索引
}
```

#### 5. 性能保护示例
```python
# 恶意的大偏移量查询会被自动限制
query_builder.apply_pagination(PageParams(page=999999, size=10))
# 页码会被自动调整到安全范围内

# 大查询限制会被自动限制
query_builder.apply_query_limit(999999)
# 限制会被自动调整到最大允许值
```

### 默认配置
```python
_query_limits = {
    'max_limit': 1000,        # 最大查询限制
    'default_limit': 50,      # 默认查询限制
    'max_offset': 10000,      # 最大偏移量（防止深度分页）
    'max_page_size': 100,     # 最大页面大小
    'default_page_size': 20,  # 默认页面大小
}
```

## 字段安全校验功能

### 概述

字段安全校验功能提供了强大的字段访问控制能力，确保只有授权的字段和关系可以被访问，防止敏感数据泄露和未授权的查询操作。

### 核心特性

1. **白名单/黑名单控制**
   - 支持字段级别的白名单和黑名单
   - 支持关系级别的白名单和黑名单
   - 自动检测配置冲突

2. **基于权限的访问控制**
   - 5个权限级别：read、filter、sort、write、admin
   - 权限继承机制（高级权限包含低级权限）
   - 支持字段和关系的独立权限配置

3. **批量验证**
   - 支持字段列表的批量安全验证
   - 优雅的错误处理和日志记录
   - 支持配置缓存和复用

4. **集成支持**
   - 与 QueryBuilder 无缝集成
   - 与 JsonSpecParser 集成
   - 支持动态配置管理

### 使用场景

#### 1. 基本安全控制
```python
# 创建安全配置
security_config = FieldSecurityConfig(
    allowed_fields={"id", "username", "email", "department"},
    forbidden_fields={"password_hash", "salary"}
)

# 创建字段解析器
resolver = FieldResolver(UserPO, security_config)

# 验证字段访问
try:
    field = resolver.resolve("username", operation="read")
    print("✓ 允许访问")
except FieldSecurityError as e:
    print(f"✗ 访问被拒绝: {e}")
```

#### 2. 基于用户角色的权限管理
```python
# 定义用户权限
user_permissions = {
    "id": "read",
    "username": "read",
    "email": "read",
    "phone": "filter",
    "salary": "forbidden",
    "password_hash": "forbidden"
}

# 创建用户配置
config = field_security_manager.create_user_config(user_permissions)
resolver = FieldResolver(UserPO, config)
```

#### 3. 查询构建器集成
```python
# 创建安全的查询构建器
field_resolver = FieldResolver(UserPO, security_config)
query_builder = QueryBuilder(UserPO, field_resolver)

# 应用过滤条件（自动进行安全验证）
filters = [
    Filter(field="username", operator=FilterOperator.LIKE, value="john%"),
    Filter(field="email", operator=FilterOperator.EQUALS, value="john@example.com"),
    # 这个会被安全验证拒绝
    Filter(field="password_hash", operator=FilterOperator.EQUALS, value="hash123")
]

query_builder.apply_filters(filters)
```

### 安全管理器

`FieldSecurityManager` 提供了全局的安全配置管理功能：

```python
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import field_security_manager

# 注册预定义配置
public_config = FieldSecurityConfig(
    allowed_fields={"id", "username", "department"},
    forbidden_fields={"password_hash", "salary", "phone", "email"}
)

field_security_manager.register_config("public", public_config)

# 在需要时获取配置
config = field_security_manager.get_config("public")
resolver = FieldResolver(UserPO, config)
```

## 高级功能

### 1. 显式 Join 支持

QueryBuilder 支持显式的 join 声明：

```python
# 定义 join 配置
joins = [
    {
        "path": "manager",
        "type": "left",
        "alias": "mgr",
        "on": "manager.id = user.manager_id"
    }
]

# 应用 joins
query_builder.apply_joins(joins)
```

### 2. 统计函数支持

支持各种统计函数：

```python
# 定义统计函数
statistics = [
    Statistic(field="salary", function=StatisticalFunction.AVG, alias="avg_salary"),
    Statistic(field="id", function=StatisticalFunction.COUNT, alias="total_count")
]

# 应用统计函数
query_builder.apply_statistics(statistics)
```

### 3. 字段选择优化

支持精确的字段选择：

```python
# 选择特定字段
fields = ["id", "username", "email", "department.name"]

# 应用字段选择
query_builder.apply_field_selection(fields)
```

## 最佳实践

### 1. 安全配置管理

```python
def create_dynamic_config(user_context: UserContext) -> FieldSecurityConfig:
    """根据用户上下文创建动态安全配置"""
    if user_context.is_admin:
        return FieldSecurityConfig()  # 管理员无限制
    elif user_context.is_manager:
        return FieldSecurityConfig(
            allowed_fields={"id", "username", "email", "department"},
            forbidden_fields={"password_hash", "salary"}
        )
    else:
        return FieldSecurityConfig(
            allowed_fields={"id", "username", "department"},
            forbidden_fields={"password_hash", "salary", "email", "phone"}
        )
```

### 2. 错误处理

```python
try:
    field = resolver.resolve("sensitive_field", operation="read")
except FieldSecurityError as e:
    # 记录安全事件
    logger.warning(f"Field access denied: {e}")
    # 返回默认值或抛出业务异常
    raise BusinessError("Access denied")
```

### 3. 性能优化

```python
# 使用配置缓存
@lru_cache(maxsize=128)
def get_security_config(user_role: str) -> FieldSecurityConfig:
    return field_security_manager.get_config(user_role) or create_default_config()
```

## 测试

运行测试以确保功能正确性：

```bash
# 运行字段安全校验测试
pytest tests/test_field_security.py -v

# 运行所有 helper 模块测试
pytest tests/ -v
```

## 总结

Repository Helper 模块提供了完整的查询构建和安全校验解决方案，通过模块化设计实现了高度的可扩展性和可维护性。字段安全校验功能确保了数据访问的安全性，而查询构建器提供了强大的查询能力，两者结合为构建安全可靠的数据访问层提供了坚实的基础。 