# Repository Mixins 使用指南

## 概述

Bento Framework 的 Repository 增强功能通过 8 个 Mixin 模块提供了 29 个常用方法，极大提升了开发效率。所有继承自 `BaseRepository` 或 `RepositoryAdapter` 的类自动获得这些功能。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   RepositoryAdapter (AR层)               │
│  ┌──────────────────────────────────────────────────┐  │
│  │  8个 Adapter Mixins (29个方法)                   │  │
│  │  • BatchOperationsMixin                          │  │
│  │  • UniquenessChecksMixin                         │  │
│  │  • AggregateQueryMixin                           │  │
│  │  • SortingLimitingMixin                          │  │
│  │  • ConditionalUpdateMixin                        │  │
│  │  • GroupByQueryMixin                             │  │
│  │  • SoftDeleteEnhancedMixin                       │  │
│  │  • RandomSamplingMixin                           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↓ 委托
┌─────────────────────────────────────────────────────────┐
│                   BaseRepository (PO层)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  8个 BaseRepository Mixins (29个方法)            │  │
│  │  实现具体的数据库操作                            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 基本使用

所有 Repository 自动继承增强功能，无需任何配置：

```python
from bento.infrastructure.repository import RepositoryAdapter
from bento.core.ids import ID

class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
    pass  # 自动获得 29 个增强方法
```

### 2. 立即使用

```python
# 在 Application Service 中
class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self._repo = product_repo

    async def get_featured_products(self) -> list[Product]:
        # 使用增强方法：随机获取 10 个产品
        return await self._repo.find_random_n(10)

    async def get_category_stats(self) -> dict[str, int]:
        # 使用增强方法：按类别分组统计
        return await self._repo.group_by_field("category_id")
```

## P0: 基础增强 (6个方法)

### 批量 ID 操作

#### `get_by_ids(ids: list[ID]) -> list[AR]`

批量获取多个实体。

```python
# 批量获取订单
order_ids = ["order-1", "order-2", "order-3"]
orders = await order_repo.get_by_ids(order_ids)

# 效率对比
# ❌ 传统方式：N次查询
for order_id in order_ids:
    order = await order_repo.get_by_id(order_id)

# ✅ 增强方式：1次查询
orders = await order_repo.get_by_ids(order_ids)
```

#### `exists_by_id(entity_id: ID) -> bool`

快速检查ID是否存在。

```python
# 验证订单存在性
if await order_repo.exists_by_id(order_id):
    print("订单存在")
else:
    raise OrderNotFoundError()

# 批量验证
valid_ids = [
    order_id for order_id in candidate_ids
    if await order_repo.exists_by_id(order_id)
]
```

#### `delete_by_ids(ids: list[ID]) -> int`

批量删除实体（硬删除，性能优化，绕过拦截器）。

```python
# 清理过期数据
expired_ids = ["id1", "id2", "id3"]
deleted_count = await data_repo.delete_by_ids(expired_ids)
print(f"删除了 {deleted_count} 条记录")
```

### 唯一性检查

#### `is_unique(field: str, value: Any, exclude_id: ID | None = None) -> bool`

验证字段值唯一性。

```python
# 创建用户前检查邮箱
if not await user_repo.is_unique("email", "user@example.com"):
    raise EmailAlreadyExistsError()

# 更新时排除自身
if not await user_repo.is_unique("email", new_email, exclude_id=user.id):
    raise EmailAlreadyExistsError()
```

#### `find_by_field(field: str, value: Any) -> AR | None`

通过字段值查找实体。

```python
# 通过邮箱查找用户
user = await user_repo.find_by_field("email", "admin@example.com")

# 通过 SKU 查找产品
product = await product_repo.find_by_field("sku", "PROD-001")
```

#### `find_all_by_field(field: str, value: Any) -> list[AR]`

查找所有匹配的实体。

```python
# 查找某客户的所有订单
orders = await order_repo.find_all_by_field("customer_id", customer.id)

# 查找某类别的所有产品
products = await product_repo.find_all_by_field("category_id", "electronics")
```

## P1: 高级查询 (13个方法)

### 聚合查询

#### `sum_field(field: str, spec: Spec | None = None) -> float`

对字段值求和。

```python
# 统计总收入
total_revenue = await order_repo.sum_field("total")

# 统计特定时间段的收入
spec = OrderSpec().created_after(start_date).created_before(end_date)
period_revenue = await order_repo.sum_field("total", spec)
```

#### `avg_field(field: str, spec: Spec | None = None) -> float`

计算字段平均值。

```python
# 平均订单金额
avg_order = await order_repo.avg_field("total")

# 活跃用户平均消费
active_spec = UserSpec().is_active()
avg_spending = await order_repo.avg_field("total", active_spec)
```

#### `min_field(field: str, spec: Spec | None = None) -> Any`

查找字段最小值。

```python
# 最低价格
min_price = await product_repo.min_field("price")
```

#### `max_field(field: str, spec: Spec | None = None) -> Any`

查找字段最大值。

```python
# 最高价格
max_price = await product_repo.max_field("price")
```

#### `count_field(field: str, spec: Spec | None = None, distinct: bool = False) -> int`

计数字段值。

```python
# 总订单数
total_orders = await order_repo.count_field("id")

# 不同客户数
unique_customers = await order_repo.count_field("customer_id", distinct=True)
```

### 排序和限制

#### `find_first(spec: Spec | None = None, order_by: str | None = None) -> AR | None`

查找第一个实体。

```python
# 第一个用户
first_user = await user_repo.find_first()

# 最新订单
latest_order = await order_repo.find_first(order_by="-created_at")

# 价格最低的产品
cheapest = await product_repo.find_first(order_by="price")
```

#### `find_last(spec: Spec | None = None, order_by: str | None = None) -> AR | None`

查找最后一个实体。

```python
# 最后一个订单
last_order = await order_repo.find_last(order_by="created_at")
```

#### `find_top_n(n: int, spec: Spec | None = None, order_by: str | None = None) -> list[AR]`

查找前N个实体。

```python
# 最新10个订单
latest_10 = await order_repo.find_top_n(10, order_by="-created_at")

# 价格最高的5个产品
top_5_expensive = await product_repo.find_top_n(5, order_by="-price")

# 评分最高的活跃产品
active_spec = ProductSpec().is_active()
top_rated = await product_repo.find_top_n(10, active_spec, order_by="-rating")
```

#### `find_paginated(page: int, page_size: int, spec: Spec | None = None, order_by: str | None = None) -> tuple[list[AR], int]`

分页查询。

```python
# 第1页，每页20条
products, total = await product_repo.find_paginated(
    page=1,
    page_size=20,
    order_by="name"
)
print(f"显示 {len(products)}/{total} 个产品")

# 计算总页数
total_pages = (total + page_size - 1) // page_size
```

### 条件更新/删除

#### `update_by_spec(spec: Spec, updates: dict[str, Any]) -> int`

批量更新匹配的实体。

```python
# 取消所有超过30天的待处理订单
spec = OrderSpec().status_equals("PENDING").older_than(days=30)
count = await order_repo.update_by_spec(spec, {
    "status": "CANCELLED",
    "cancelled_at": datetime.now()
})
print(f"取消了 {count} 个订单")

# 停用不活跃用户
spec = UserSpec().last_login_before(days=180)
await user_repo.update_by_spec(spec, {"is_active": False})
```

⚠️ **注意**：此方法绕过拦截器以提升性能，不会自动更新审计字段。

#### `delete_by_spec(spec: Spec) -> int`

批量删除匹配的实体。

```python
# 删除所有已完成的订单
spec = OrderSpec().status_equals("COMPLETED")
deleted = await order_repo.delete_by_spec(spec)
```

#### `soft_delete_by_spec(spec: Spec) -> int`

批量软删除。

```python
# 软删除过期产品
spec = ProductSpec().expired()
count = await product_repo.soft_delete_by_spec(spec)
```

#### `restore_by_spec(spec: Spec) -> int`

批量恢复软删除的实体。

```python
# 恢复最近7天内删除的用户
spec = UserSpec().deleted_within_days(7)
count = await user_repo.restore_by_spec(spec)
```

## P2: 分析增强 (7个方法)

### 分组查询

#### `group_by_field(field: str, spec: Spec | None = None) -> dict[Any, int]`

按字段分组统计。

```python
# 订单状态分布
status_counts = await order_repo.group_by_field("status")
# 结果: {"PENDING": 10, "PAID": 25, "SHIPPED": 15}

# 产品类别分布
category_counts = await product_repo.group_by_field("category_id")

# 活跃用户的订单状态分布
active_spec = OrderSpec().is_active()
stats = await order_repo.group_by_field("status", active_spec)
```

#### `group_by_date(date_field: str, granularity: str = "day", spec: Spec | None = None) -> dict[str, int]`

按日期分组统计。

```python
# 每日订单统计
daily = await order_repo.group_by_date("created_at", "day")
# 结果: {"2025-01-01": 5, "2025-01-02": 8, ...}

# 每周统计
weekly = await order_repo.group_by_date("created_at", "week")
# 结果: {"2025-W01": 35, "2025-W02": 42, ...}

# 每月统计
monthly = await order_repo.group_by_date("created_at", "month")
# 结果: {"2025-01": 150, "2025-02": 180, ...}

# 每年统计
yearly = await order_repo.group_by_date("created_at", "year")
# 结果: {"2025": 1850, "2024": 1650}
```

支持的粒度：`"day"`, `"week"`, `"month"`, `"year"`

#### `group_by_multiple_fields(fields: list[str], spec: Spec | None = None) -> dict[tuple, int]`

按多个字段分组统计。

```python
# 按状态和客户分组
counts = await order_repo.group_by_multiple_fields(["status", "customer_id"])
# 结果: {("PENDING", "c1"): 3, ("PAID", "c1"): 5, ("PAID", "c2"): 2}

# 按类别和品牌分组
product_stats = await product_repo.group_by_multiple_fields(
    ["category_id", "brand_id"]
)
```

### 软删除增强

#### `find_trashed(spec: Spec | None = None) -> list[AR]`

查找所有软删除的实体。

```python
# 查看回收站
trashed_users = await user_repo.find_trashed()

# 查找最近删除的订单
recent_spec = OrderSpec().deleted_within_days(7)
recent_trashed = await order_repo.find_trashed(recent_spec)
```

#### `find_with_trashed(spec: Spec | None = None) -> list[AR]`

查找所有实体（包括已删除）。

```python
# 获取客户的所有订单（包括已删除）
spec = OrderSpec().customer_id_equals(customer.id)
all_orders = await order_repo.find_with_trashed(spec)
```

#### `count_trashed(spec: Spec | None = None) -> int`

统计软删除的实体数量。

```python
# 回收站中的用户数
trashed_count = await user_repo.count_trashed()
print(f"回收站有 {trashed_count} 个用户")
```

#### `is_trashed(entity_id: ID) -> bool`

检查实体是否已被软删除。

```python
# 检查订单是否在回收站
if await order_repo.is_trashed(order_id):
    print("该订单已被删除")
```

## P3: 特殊功能 (3个方法)

### 随机采样

#### `find_random(spec: Spec | None = None) -> AR | None`

随机获取一个实体。

```python
# 随机推荐一个产品
random_product = await product_repo.find_random()

# 随机选择一个活跃用户
active_spec = UserSpec().is_active()
random_user = await user_repo.find_random(active_spec)
```

#### `find_random_n(n: int, spec: Spec | None = None) -> list[AR]`

随机获取N个实体。

```python
# 随机推荐5个产品
recommendations = await product_repo.find_random_n(5)

# 随机选择3个活跃产品
active_spec = ProductSpec().is_active()
featured = await product_repo.find_random_n(3, active_spec)
```

#### `sample_percentage(percentage: float, spec: Spec | None = None, max_count: int | None = None) -> list[AR]`

按百分比随机采样。

```python
# 抽取10%的订单用于审计
sample = await order_repo.sample_percentage(10.0)

# 抽取5%的活跃用户，最多1000个
active_spec = UserSpec().is_active()
sample_users = await user_repo.sample_percentage(
    5.0,
    active_spec,
    max_count=1000
)
```

## 实战案例

### 案例1：电商分析面板

```python
class OrderAnalyticsService:
    def __init__(self, order_repo: OrderRepository):
        self._repo = order_repo

    async def get_dashboard_stats(self, start_date: date, end_date: date):
        # 时间范围筛选
        spec = OrderSpec().created_between(start_date, end_date)

        # 总收入
        total_revenue = await self._repo.sum_field("total", spec)

        # 平均订单金额
        avg_order_value = await self._repo.avg_field("total", spec)

        # 订单状态分布
        status_distribution = await self._repo.group_by_field("status", spec)

        # 每日订单趋势
        daily_orders = await self._repo.group_by_date("created_at", "day", spec)

        # 不同客户数
        unique_customers = await self._repo.count_field(
            "customer_id", spec, distinct=True
        )

        return {
            "total_revenue": total_revenue,
            "avg_order_value": avg_order_value,
            "status_distribution": status_distribution,
            "daily_trend": daily_orders,
            "unique_customers": unique_customers
        }
```

### 案例2：数据清理任务

```python
class DataCleanupService:
    def __init__(self, order_repo: OrderRepository, user_repo: UserRepository):
        self._order_repo = order_repo
        self._user_repo = user_repo

    async def cleanup_old_data(self):
        # 取消超过30天的待处理订单
        old_pending_spec = OrderSpec() \\
            .status_equals("PENDING") \\
            .older_than(days=30)
        cancelled = await self._order_repo.update_by_spec(
            old_pending_spec,
            {"status": "CANCELLED", "reason": "Timeout"}
        )

        # 删除90天前的已完成订单
        old_completed_spec = OrderSpec() \\
            .status_equals("COMPLETED") \\
            .older_than(days=90)
        deleted = await self._order_repo.delete_by_spec(old_completed_spec)

        # 停用180天未登录的用户
        inactive_spec = UserSpec().last_login_before(days=180)
        deactivated = await self._user_repo.update_by_spec(
            inactive_spec,
            {"is_active": False}
        )

        return {
            "cancelled_orders": cancelled,
            "deleted_orders": deleted,
            "deactivated_users": deactivated
        }
```

### 案例3：智能推荐系统

```python
class RecommendationService:
    def __init__(self, product_repo: ProductRepository):
        self._repo = product_repo

    async def get_recommendations(self, user: User, count: int = 10):
        # 基于用户偏好的规格
        preference_spec = ProductSpec() \\
            .is_active() \\
            .in_categories(user.preferred_categories) \\
            .price_between(user.min_price, user.max_price)

        # 随机推荐N个符合条件的产品
        recommendations = await self._repo.find_random_n(count, preference_spec)

        # 如果不足，补充随机产品
        if len(recommendations) < count:
            remaining = count - len(recommendations)
            active_spec = ProductSpec().is_active()
            more = await self._repo.find_random_n(remaining, active_spec)
            recommendations.extend(more)

        return recommendations
```

## 性能优化建议

### 1. 批量操作优先

```python
# ❌ 避免：循环单次查询
for user_id in user_ids:
    user = await repo.get_by_id(user_id)

# ✅ 推荐：批量查询
users = await repo.get_by_ids(user_ids)
```

### 2. 使用 Specification 过滤

```python
# ❌ 避免：加载所有数据后过滤
all_users = await repo.find_all()
active = [u for u in all_users if u.is_active]

# ✅ 推荐：数据库层面过滤
active_spec = UserSpec().is_active()
active = await repo.find(active_spec)
```

### 3. 合理使用聚合查询

```python
# ❌ 避免：加载所有数据计算
all_orders = await repo.find_all()
total = sum(o.total for o in all_orders)

# ✅ 推荐：使用数据库聚合
total = await repo.sum_field("total")
```

### 4. 分页大数据集

```python
# ❌ 避免：一次加载所有数据
all_products = await repo.find_all()

# ✅ 推荐：分页加载
products, total = await repo.find_paginated(page=1, page_size=50)
```

## 最佳实践

### 1. 在 Application Service 中使用

```python
class UserApplicationService:
    def __init__(self, user_repo: UserRepository):
        self._repo = user_repo

    async def register_user(self, command: RegisterUserCommand) -> User:
        # 使用唯一性检查
        if not await self._repo.is_unique("email", command.email):
            raise EmailAlreadyExistsError()

        user = User.create(command.email, command.name)
        await self._repo.save(user)
        return user
```

### 2. 结合 Specification 模式

```python
# 定义可复用的规格
class ProductSpec(CompositeSpecification):
    def is_active(self) -> Self:
        return self.and_spec(FieldEquals("is_active", True))

    def in_category(self, category_id: str) -> Self:
        return self.and_spec(FieldEquals("category_id", category_id))

    def price_between(self, min_price: int, max_price: int) -> Self:
        spec = FieldGreaterThanOrEquals("price", min_price)
        spec = spec.and_spec(FieldLessThanOrEquals("price", max_price))
        return self.and_spec(spec)

# 使用规格查询
spec = ProductSpec().is_active().in_category("electronics").price_between(100, 1000)
products = await product_repo.find_top_n(10, spec, order_by="-rating")
```

### 3. 错误处理

```python
async def get_product_stats(self, category_id: str):
    try:
        spec = ProductSpec().in_category(category_id)

        count = await self._repo.count_field("id", spec)
        if count == 0:
            raise CategoryEmptyError(category_id)

        avg_price = await self._repo.avg_field("price", spec)
        return {"count": count, "avg_price": avg_price}

    except ValueError as e:
        # 处理无效参数
        raise InvalidCategoryError(str(e))
```

## 常见问题

### Q1: 方法会自动处理软删除吗？

A: 大多数查询方法会自动排除软删除的记录（如果实体有 `deleted_at` 字段）。使用 `find_with_trashed` 可以包含已删除记录。

### Q2: 批量操作是否触发领域事件？

A: `update_by_spec`、`delete_by_spec` 等批量操作绕过拦截器，不会触发领域事件。如需事件，请使用单个实体操作。

### Q3: 如何处理大数据量？

A: 使用分页 (`find_paginated`) 或采样 (`sample_percentage`) 方法，避免一次加载所有数据。

### Q4: 能在事务中使用吗？

A: 可以。所有方法都使用当前的 Session，支持事务操作。

### Q5: 性能如何？

A: 所有操作都在数据库层面执行，性能优异。批量操作通常比循环单次操作快10-100倍。

## 总结

Repository Mixins 提供了一套完整、高效、易用的数据访问增强功能：

- ✅ **零配置**：自动继承，立即可用
- ✅ **类型安全**：完整的类型注解
- ✅ **高性能**：数据库层面执行
- ✅ **易测试**：70+单元测试覆盖
- ✅ **好维护**：模块化设计

通过合理使用这些方法，可以显著提升开发效率，减少样板代码，让你专注于业务逻辑！
