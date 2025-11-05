# 分页和查询限制功能指南

## 概述

QueryBuilder 提供了强大的分页和查询限制功能，支持多种分页方式，并内置性能保护机制，防止恶意查询对系统造成性能影响。

## 主要特性

### 1. 多种分页方式
- **页码分页**：使用 page/size 参数
- **偏移量分页**：使用 offset/limit 参数
- **游标分页**：适用于大数据量场景
- **智能分页**：自动处理边界情况

### 2. 性能保护
- **查询限制**：防止返回过多结果
- **偏移量限制**：防止深度分页性能问题
- **参数验证**：自动修正无效参数
- **默认限制**：确保查询性能

### 3. 可配置性
- **灵活配置**：支持自定义各种限制参数
- **环境适配**：可根据不同环境调整限制
- **安全策略**：支持不同安全级别的配置

## 配置参数

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

### 自定义配置
```python
# 设置自定义查询限制
query_builder.set_query_limits(
    max_limit=500,
    default_limit=25,
    max_offset=5000,
    max_page_size=50,
    default_page_size=10
)
```

## 使用方法

### 1. 基本分页

#### 页码分页
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

#### 偏移量分页
```python
@dataclass
class OffsetLimitParams:
    offset: int = 0
    limit: int = 50

# 创建偏移量分页参数
offset_limit = OffsetLimitParams(offset=100, limit=25)

# 应用分页
query_builder.apply_pagination(offset_limit)
```

### 2. 智能分页
```python
# 自动处理边界情况
query_builder.apply_smart_pagination(
    page_num=2,      # 页码
    page_size=15,    # 页面大小
    max_pages=100    # 最大页码限制（可选）
)
```

### 3. 查询限制
```python
# 应用默认查询限制
query_builder.apply_query_limit()

# 应用自定义查询限制
query_builder.apply_query_limit(100)

# 应用偏移量
query_builder.apply_offset(50)
```

### 4. 游标分页
```python
# 应用游标分页
query_builder.apply_cursor_pagination(
    cursor="user_123",  # 游标值
    limit=20           # 限制数量
)
```

## 参数验证

### 自动验证和修正
```python
# 验证分页参数
page_num, page_size = query_builder.validate_pagination_params(0, 200)

# 参数会被自动修正：
# - 页码为0会被修正为1
# - 页面大小200会被限制为100（最大页面大小）
```

### 验证规则
1. **页码**：最小值为1
2. **页面大小**：最小值为1，最大值为配置的最大页面大小
3. **偏移量**：最小值为0，最大值为配置的最大偏移量
4. **查询限制**：最小值为1，最大值为配置的最大查询限制

## 分页信息

### 获取分页信息
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

## 性能保护

### 1. 防止恶意查询
```python
# 恶意的大偏移量查询会被自动限制
query_builder.apply_pagination(PageParams(page=999999, size=10))
# 页码会被自动调整到安全范围内
```

### 2. 防止大结果集
```python
# 大查询限制会被自动限制
query_builder.apply_query_limit(999999)
# 限制会被自动调整到最大允许值
```

### 3. 深度分页保护
```python
# 深度分页会被检测并限制
page_num, page_size = query_builder.validate_pagination_params(1000, 10)
offset = (page_num - 1) * page_size
# 如果偏移量超过最大限制，页码会被调整
```

## 与其他功能集成

### 1. 与过滤条件集成
```python
# 应用过滤条件
filters = [
    Filter(field="username", operator=FilterOperator.LIKE, value="john%"),
    Filter(field="email", operator=FilterOperator.CONTAINS, value="@example.com"),
]
query_builder.apply_filters(filters)

# 应用分页
query_builder.apply_pagination(PageParams(page=1, size=15))
```

### 2. 与JOIN去重集成
```python
# 应用JOIN
query_builder.apply_joins([
    {"path": "orders", "type": "left", "alias": "o"}
])

# 应用分页（JOIN信息会被保留）
query_builder.apply_pagination(PageParams(page=1, size=20))
```

### 3. 与字段安全集成
```python
# 字段安全验证会在分页前进行
query_builder.apply_field_selection(["id", "username", "email"])
query_builder.apply_pagination(PageParams(page=1, size=10))
```

## 最佳实践

### 1. 配置合理的限制
```python
# 根据系统性能配置合适的限制
query_builder.set_query_limits(
    max_limit=500,        # 根据数据库性能调整
    max_offset=5000,      # 防止深度分页
    max_page_size=50,     # 控制单页数据量
)
```

### 2. 使用智能分页
```python
# 推荐使用智能分页，自动处理边界情况
query_builder.apply_smart_pagination(page_num=1, page_size=20)
```

### 3. 提供分页信息
```python
# 在API响应中提供完整的分页信息
pagination_info = query_builder.get_pagination_info(page_num, page_size, total_count)
response = {
    'data': results,
    'pagination': pagination_info
}
```

### 4. 监控查询性能
```python
# 记录查询统计信息
join_stats = query_builder.get_join_statistics()
# 监控JOIN数量和复杂度
```

## 错误处理

### 1. 参数验证错误
```python
try:
    page_num, page_size = query_builder.validate_pagination_params(-1, 0)
except ValueError as e:
    # 处理参数错误
    pass
```

### 2. 性能保护触发
```python
# 当性能保护触发时，参数会被自动调整
# 建议记录日志以便监控
import logging
logging.info(f"Pagination parameters adjusted: {original_params} -> {adjusted_params}")
```

## 测试

### 运行测试
```bash
# 运行分页功能测试
python -m pytest tests/test_pagination.py -v

# 运行示例
python src/idp/framework/infrastructure/persistence/sqlalchemy/repository/helper/pagination_example.py
```

### 测试覆盖
- 基本分页功能
- 参数验证和修正
- 性能保护机制
- 边界情况处理
- 与其他功能集成

## 总结

QueryBuilder 的分页和查询限制功能提供了：

1. **完整的解决方案**：支持多种分页方式
2. **性能保护**：防止恶意查询和性能问题
3. **灵活配置**：可根据需求调整限制参数
4. **易于使用**：简单的API和自动参数验证
5. **安全可靠**：内置安全验证和错误处理

这些功能确保了查询系统的稳定性、性能和安全性，是企业级应用的重要保障。 