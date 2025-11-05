# Python Specification Pattern Implementation

一个功能强大、类型安全且易于扩展的规格模式实现，专为 Python DDD (领域驱动设计) 项目设计。

## 特性

- 🎯 完整的类型提示支持
- 🔍 丰富的查询操作符
- 🏗️ 流式构建器API
- 🎨 优雅的查询组合
- 📦 易于扩展的架构
- 🔒 内置验证机制
- 🚀 支持复杂查询场景

## 快速开始

### 基础查询

```python
from idp.domain.persistence.spec import SpecificationBuilder

# 创建简单查询
spec = (SpecificationBuilder()
    .filter("is_active", True)
    .where("price", ">=", 100)
    .build())

# 使用查询
results = await repository.find_by_specification(spec)
```

### 复杂条件组合

```python
# AND/OR 组合
spec = (SpecificationBuilder()
    .and_(
        lambda b: b.filter("status", "active"),
        lambda b: b.where("price", ">=", 1000)
    )
    .or_(
        lambda b: b.where("category", "in", ["vip", "premium"]),
        lambda b: b.where("rating", ">", 4.5)
    )
    .build())
```

## 核心概念

### 1. 规格构建器

提供三种专门的构建器：

- `SpecificationBuilder`: 基础查询构建器
- `EntitySpecificationBuilder`: 实体查询构建器
- `AggregateSpecificationBuilder`: 聚合查询构建器

### 2. 操作符支持

#### 标准操作符
- 相等: `eq`, `ne`
- 比较: `gt`, `ge`, `lt`, `le`
- 集合: `in`, `not_in`
- 范围: `between`
- 空值: `is_null`, `is_not_null`

#### 文本操作符
- 模式匹配: `like`, `ilike`
- 包含: `contains`, `not_contains`
- 前缀/后缀: `starts_with`, `ends_with`
- 正则表达式: `regex`, `iregex`

#### 数组操作符
- 数组包含: `array_contains`
- 数组重叠: `array_overlaps`
- 数组空值: `array_empty`, `array_not_empty`

#### JSON操作符
- JSON包含: `json_contains`
- JSON存在: `json_exists`
- JSON键检查: `json_has_key`

### 3. 实体查询

```python
from idp.domain.persistence.spec import EntitySpecificationBuilder

# 使用实体构建器
spec = (EntitySpecificationBuilder()
    .is_active()
    .created_in_last_days(7)
    .updated_between(start_date, end_date)
    .build())
```

### 4. 聚合查询

```python
from idp.domain.persistence.spec import AggregateSpecificationBuilder

# 使用聚合构建器
spec = (AggregateSpecificationBuilder()
    .group_by("category")
    .sum("price", alias="total_price")
    .avg("rating", alias="average_rating")
    .having("total_price", ">=", 1000)
    .build())
```

## 高级用法

### 1. 分页和排序

```python
spec = (SpecificationBuilder()
    .filter("is_active", True)
    .add_sort("created_at", ascending=False)
    .add_sort("id", ascending=True)
    .set_page(offset=0, limit=20)
    .build())
```

### 2. 字段选择和关联加载

```python
spec = (SpecificationBuilder()
    .select("id", "name", "price", "category")
    .include("manufacturer", "reviews")
    .build())
```

### 3. 日期查询

```python
spec = (EntitySpecificationBuilder()
    .created_in_last_days(7)
    .created_in_month(2024, 3)
    .created_between(start_date, end_date)
    .build())
```

### 4. 统计查询

```python
spec = (AggregateSpecificationBuilder()
    .group_by("category", "status")
    .count("id", alias="total")
    .sum("amount", alias="total_amount")
    .avg("price", alias="average_price")
    .having("total", ">", 5)
    .build())
```

## 实际应用示例

### 1. 订单查询

```python
def find_recent_orders(days: int = 7) -> Specification:
    return (EntitySpecificationBuilder()
        .created_in_last_days(days)
        .filter("status", "active")
        .add_sort("created_at", ascending=False)
        .build())
```

### 2. 产品搜索

```python
def search_products(
    search_text: str,
    categories: List[str],
    min_price: Decimal
) -> Specification:
    return (SpecificationBuilder()
        .or_(
            lambda b: b.text_search("name", search_text),
            lambda b: b.text_search("description", search_text)
        )
        .where("category", "in", categories)
        .where("price", ">=", min_price)
        .filter("is_active", True)
        .build())
```

### 3. 销售统计

```python
def get_sales_statistics(start_date: datetime, end_date: datetime) -> Specification:
    return (AggregateSpecificationBuilder()
        .between("order_date", start_date, end_date)
        .group_by("product_category")
        .sum("amount", alias="total_sales")
        .count("id", alias="order_count")
        .having("total_sales", ">=", 1000)
        .add_sort("total_sales", ascending=False)
        .build())
```

## 更多实际应用示例

### 4. 用户权限查询

```python
def find_user_permissions(user_id: UUID, resource: str) -> Specification:
    return (SpecificationBuilder()
        .filter("user_id", str(user_id))
        .filter("resource", resource)
        .and_(
            lambda b: b.filter("is_active", True),
            lambda b: b.or_(
                lambda b: b.is_null("expires_at"),
                lambda b: b.where("expires_at", ">", datetime.now())
            )
        )
        .select("id", "resource", "action", "granted_at")
        .include("role.permissions")
        .build())
```

### 5. 库存管理查询

```python
def find_low_stock_products(threshold: int, categories: List[str]) -> Specification:
    return (SpecificationBuilder()
        .where("stock_level", "<=", threshold)
        .where("category", "in", categories)
        .filter("is_active", True)
        .and_(
            lambda b: b.where("reorder_point", ">=", threshold),
            lambda b: b.is_null("last_order_date")
        )
        .add_sort("stock_level")
        .include("supplier")
        .build())
```

### 6. 复杂报表查询

```python
def generate_sales_report(
    start_date: datetime,
    end_date: datetime,
    categories: List[str]
) -> Specification:
    return (AggregateSpecificationBuilder()
        .between("order_date", start_date, end_date)
        .where("category", "in", categories)
        .filter("status", "completed")
        .group_by("category", "product_id")
        .sum("quantity", alias="total_quantity")
        .sum("amount", alias="total_amount")
        .avg("unit_price", alias="average_price")
        .count("order_id", alias="order_count", distinct=True)
        .having("total_amount", ">=", 10000)
        .add_sort("total_amount", ascending=False)
        .build())
```

### 7. 客户分析查询

```python
def analyze_customer_behavior(days: int) -> Specification:
    return (AggregateSpecificationBuilder()
        .created_in_last_days(days)
        .group_by("customer_id", "product_category")
        .sum("purchase_amount", alias="total_spent")
        .count("id", alias="purchase_count")
        .avg("basket_size", alias="average_basket")
        .having("purchase_count", ">=", 3)
        .add_sort("total_spent", ascending=False)
        .build())
```

## 最佳实践

1. **使用类型提示**
   ```python
   from typing import TypeVar, List
   from uuid import UUID
   
   T = TypeVar('T', bound=Entity)
   
   def find_by_ids(ids: List[UUID]) -> Specification[T]:
       return (EntitySpecificationBuilder[T]()
           .where("id", "in", ids)
           .build())
   ```

2. **组合查询条件**
   ```python
   def get_base_query() -> SpecificationBuilder:
       return (SpecificationBuilder()
           .filter("is_active", True)
           .filter("is_deleted", False))
   
   def find_featured_products() -> Specification:
       return (get_base_query()
           .where("rating", ">=", 4.0)
           .build())
   ```

3. **使用专门的构建器**
   - 实体查询用 `EntitySpecificationBuilder`
   - 统计查询用 `AggregateSpecificationBuilder`
   - 基础查询用 `SpecificationBuilder`

4. **错误处理**
   ```python
   try:
       spec = builder.between("price", 200, 100).build()
   except ValueError as e:
       # 处理验证错误
       logger.error(f"Invalid price range: {e}")
   ```

## 扩展性

### 1. 自定义条件

```python
from idp.domain.persistence.spec.criteria import Criterion

class CustomCriterion(Criterion):
    def __init__(self, field: str, value: Any):
        self.field = field
        self.value = value
    
    def to_filter(self) -> Filter:
        return Filter(
            field=self.field,
            operator=FilterOperator.CUSTOM,
            value=self.value
        )
```

### 2. 自定义构建器

```python
class CustomBuilder(SpecificationBuilder[T]):
    def custom_query(self, param: str) -> 'CustomBuilder[T]':
        return self.add_criterion(CustomCriterion("field", param))
```

## 性能考虑

1. 使用适当的索引支持查询条件
2. 避免不必要的关联加载
3. 合理使用分页
4. 优化统计查询

## 性能优化详解

### 1. 查询优化

1. **索引策略**
   - 为常用查询字段创建适当的索引
   - 使用复合索引支持多字段查询
   - 考虑查询条件的选择性
   ```sql
   -- 示例索引
   CREATE INDEX idx_product_category_price ON products(category, price);
   CREATE INDEX idx_order_date_status ON orders(order_date, status);
   ```

2. **查询计划分析**
   - 使用 EXPLAIN 分析查询执行计划
   - 优化 JOIN 操作和子查询
   - 避免全表扫描
   ```python
   async def analyze_query(spec: Specification) -> None:
       query = spec.to_sql()
       plan = await db.execute(f"EXPLAIN ANALYZE {query}")
       logger.info(f"Query plan: {plan}")
   ```

3. **批量操作优化**
   ```python
   async def bulk_update_with_spec(spec: Specification, data: Dict) -> None:
       # 使用规格生成高效的批量更新
       query = spec.to_update_query(data)
       await db.execute(query)
   ```

### 2. 缓存策略

1. **结果缓存**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_cached_specification(category: str) -> Specification:
       return (SpecificationBuilder()
           .filter("category", category)
           .build())
   ```

2. **查询缓存**
   ```python
   async def get_with_cache(spec: Specification) -> List[Dict]:
       cache_key = spec.get_cache_key()
       result = await cache.get(cache_key)
       if not result:
           result = await repository.find_by_specification(spec)
           await cache.set(cache_key, result, ttl=3600)
       return result
   ```

### 3. 分页优化

1. **游标分页**
   ```python
   def get_cursor_based_page(cursor: str, limit: int) -> Specification:
       return (SpecificationBuilder()
           .where("id", ">", cursor)
           .add_sort("id")
           .set_page(limit=limit)
           .build())
   ```

2. **高效分页查询**
   ```python
   def get_optimized_page(
       offset: int,
       limit: int,
       last_id: Optional[str] = None
   ) -> Specification:
       builder = SpecificationBuilder()
       if last_id:
           builder.where("id", ">", last_id)
       return (builder
           .add_sort("id")
           .set_page(limit=limit)
           .build())
   ```

## 错误处理示例

### 1. 参数验证

```python
def create_date_range_spec(start_date: datetime, end_date: datetime) -> Specification:
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise ValueError("日期参数必须是 datetime 类型")
    
    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")
    
    try:
        return (SpecificationBuilder()
            .between("created_at", start_date, end_date)
            .build())
    except Exception as e:
        logger.error(f"创建日期范围规格失败: {e}")
        raise
```

### 2. 业务规则验证

```python
def create_order_spec(status: str, amount: Decimal) -> Specification:
    VALID_STATUSES = {"pending", "processing", "completed", "cancelled"}
    
    if status not in VALID_STATUSES:
        raise ValueError(f"无效的订单状态: {status}")
    
    if amount < Decimal("0"):
        raise ValueError("订单金额不能为负数")
    
    try:
        return (SpecificationBuilder()
            .filter("status", status)
            .where("amount", ">=", amount)
            .build())
    except Exception as e:
        logger.error(f"创建订单规格失败: {e}")
        raise
```

### 3. 自定义异常

```python
class SpecificationError(Exception):
    """规格相关的基础异常类"""
    pass

class InvalidFilterError(SpecificationError):
    """无效的过滤条件"""
    pass

class InvalidSortError(SpecificationError):
    """无效的排序条件"""
    pass

def create_product_spec(category: str, sort_field: str) -> Specification:
    VALID_SORT_FIELDS = {"name", "price", "created_at"}
    
    if not category:
        raise InvalidFilterError("类别不能为空")
    
    if sort_field not in VALID_SORT_FIELDS:
        raise InvalidSortError(f"无效的排序字段: {sort_field}")
    
    return (SpecificationBuilder()
        .filter("category", category)
        .add_sort(sort_field)
        .build())
```

## 数据库适配器示例

### 1. SQLAlchemy 适配器

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class SQLAlchemyAdapter:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def apply_specification(self, spec: Specification, model: Any) -> List[Any]:
        query = select(model)
        
        # 应用过滤条件
        for filter_item in spec.filters:
            query = self._apply_filter(query, filter_item)
        
        # 应用排序
        for sort_item in spec.sorts:
            query = self._apply_sort(query, sort_item)
        
        # 应用分页
        if spec.page:
            query = query.offset(spec.page.offset).limit(spec.page.limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    def _apply_filter(self, query: Any, filter_item: Filter) -> Any:
        column = getattr(query.column_descriptions[0]["entity"], filter_item.field)
        
        if filter_item.operator == FilterOperator.EQUALS:
            return query.where(column == filter_item.value)
        elif filter_item.operator == FilterOperator.IN:
            return query.where(column.in_(filter_item.value))
        # ... 其他操作符的实现
```

### 2. MongoDB 适配器

```python
from motor.motor_asyncio import AsyncIOMotorCollection

class MongoDBAdapter:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
    
    async def apply_specification(self, spec: Specification) -> List[Dict]:
        # 构建查询条件
        query = self._build_query(spec)
        
        # 构建排序条件
        sort = [(s.field, 1 if s.ascending else -1) for s in spec.sorts]
        
        # 构建投影
        projection = {field: 1 for field in spec.fields} if spec.fields else None
        
        cursor = self.collection.find(
            filter=query,
            sort=sort,
            projection=projection
        )
        
        # 应用分页
        if spec.page:
            cursor = cursor.skip(spec.page.offset).limit(spec.page.limit)
        
        return await cursor.to_list(length=None)
    
    def _build_query(self, spec: Specification) -> Dict:
        query = {}
        
        for filter_item in spec.filters:
            if filter_item.operator == FilterOperator.EQUALS:
                query[filter_item.field] = filter_item.value
            elif filter_item.operator == FilterOperator.IN:
                query[filter_item.field] = {"$in": filter_item.value}
            # ... 其他操作符的实现
        
        return query
```

### 3. Redis 适配器

```python
from redis.asyncio import Redis
import json

class RedisAdapter:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def apply_specification(self, spec: Specification, key_pattern: str) -> List[Dict]:
        # 使用 SCAN 遍历匹配的键
        keys = []
        cursor = 0
        while True:
            cursor, batch = await self.redis.scan(
                cursor=cursor,
                match=key_pattern,
                count=100
            )
            keys.extend(batch)
            if cursor == 0:
                break
        
        # 获取所有匹配键的值
        values = []
        for key in keys:
            value = await self.redis.get(key)
            if value:
                item = json.loads(value)
                if self._matches_filters(item, spec.filters):
                    values.append(item)
        
        # 应用排序
        if spec.sorts:
            values.sort(
                key=lambda x: [x[s.field] for s in spec.sorts],
                reverse=not spec.sorts[0].ascending
            )
        
        # 应用分页
        if spec.page:
            start = spec.page.offset
            end = start + spec.page.limit
            values = values[start:end]
        
        return values
    
    def _matches_filters(self, item: Dict, filters: List[Filter]) -> bool:
        for filter_item in filters:
            value = item.get(filter_item.field)
            
            if filter_item.operator == FilterOperator.EQUALS:
                if value != filter_item.value:
                    return False
            elif filter_item.operator == FilterOperator.IN:
                if value not in filter_item.value:
                    return False
            # ... 其他操作符的实现
        
        return True
```

## 贡献

欢迎贡献代码和提出建议！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多信息。

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
