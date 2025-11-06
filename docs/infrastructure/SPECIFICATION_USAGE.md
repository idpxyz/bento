# Specification 模式使用指南

**版本**: 1.0
**最后更新**: 2025-11-06

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [基础查询](#基础查询)
4. [实体查询](#实体查询)
5. [聚合根查询](#聚合根查询)
6. [软删除处理](#软删除处理)
7. [高级查询](#高级查询)
8. [Criteria 组合](#criteria-组合)
9. [与 SQLAlchemy 集成](#与-sqlalchemy-集成)
10. [最佳实践](#最佳实践)
11. [故障排查](#故障排查)

---

## 快速开始

### 前置条件

Specification 模式已内置于 Bento 框架，无需额外安装。

```bash
# 确保已安装 Bento
pip install -e .
```

### 5 分钟示例

```python
from bento.persistence.specification import EntitySpecificationBuilder

# 查询活跃用户，按创建时间降序，分页
spec = (
    EntitySpecificationBuilder()
    .where("status", "=", "active")
    .where("age", ">=", 18)
    .order_by("created_at", "desc")
    .paginate(page=1, size=20)
    .build()
)

# 使用规格查询（与 Repository 配合）
users = await user_repository.find_by_spec(spec)
```

**关键特性**：
- ✅ **类型安全**：完整的类型提示
- ✅ **链式 API**：流畅的构建器模式
- ✅ **可重用**：规格可以组合和复用
- ✅ **软删除默认**：EntitySpecificationBuilder 自动排除软删除记录
- ✅ **测试友好**：规格对象可独立测试

---

## 核心概念

### Specification 模式

Specification 模式将**查询逻辑**封装为**可重用的对象**，实现：

1. **关注点分离**：查询逻辑独立于 Repository
2. **可测试性**：规格对象可单独测试
3. **可组合性**：多个规格可以组合
4. **领域驱动**：查询语义清晰

### 核心组件

```
┌─────────────────────────────────────────┐
│     SpecificationBuilder (基础)         │
│  - where()  过滤条件                    │
│  - order_by()  排序                     │
│  - paginate()  分页                     │
└─────────────────────────────────────────┘
                   ▲
                   │
     ┌─────────────┴─────────────┐
     │                           │
┌────────────────┐    ┌──────────────────────┐
│ EntityBuilder  │    │  AggregateBuilder    │
│ 实体查询       │    │  聚合根查询          │
│ + 软删除       │    │  + 版本控制          │
│ + 审计字段     │    │  + 无默认软删除      │
└────────────────┘    └──────────────────────┘
```

### 三种 Builder

| Builder | 用途 | 默认行为 | 适用场景 |
|---------|------|----------|----------|
| `SpecificationBuilder` | 通用查询 | 无特殊处理 | 任何查询 |
| `EntitySpecificationBuilder` | 实体查询 | **自动排除软删除** | 业务实体 |
| `AggregateSpecificationBuilder` | 聚合根查询 | 支持版本控制 | DDD 聚合 |

---

## 基础查询

### 简单过滤

```python
from bento.persistence.specification import SpecificationBuilder

# 单条件查询
spec = SpecificationBuilder().where("status", "=", "active").build()

# 多条件查询 (AND)
spec = (
    SpecificationBuilder()
    .where("status", "=", "active")
    .where("age", ">=", 18)
    .where("age", "<", 65)
    .build()
)
```

### 支持的操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `=`, `==` | 等于 | `.where("id", "=", 123)` |
| `!=`, `<>` | 不等于 | `.where("status", "!=", "deleted")` |
| `>`, `>=`, `<`, `<=` | 比较 | `.where("age", ">=", 18)` |
| `in` | 在列表中 | `.where("status", "in", ["active", "pending"])` |
| `not in` | 不在列表中 | `.where("role", "not in", ["guest"])` |
| `like` | 模糊匹配 | `.where("name", "like", "%John%")` |
| `ilike` | 不区分大小写 | `.where("email", "ilike", "%@gmail.com")` |
| `is null` | 为空 | `.where("deleted_at", "is null", None)` |
| `is not null` | 不为空 | `.where("email", "is not null", None)` |
| `between` | 范围 | 使用 `BetweenCriterion` |

### 排序和分页

```python
from bento.persistence.specification import SortDirection

# 排序
spec = (
    SpecificationBuilder()
    .where("status", "=", "active")
    .order_by("created_at", SortDirection.DESC)  # 降序
    .order_by("name", SortDirection.ASC)         # 升序
    .build()
)

# 分页
spec = (
    SpecificationBuilder()
    .where("status", "=", "active")
    .paginate(page=2, size=20)  # 第2页，每页20条
    .build()
)

# 访问分页信息
print(f"Page: {spec.page.page}")
print(f"Size: {spec.page.size}")
print(f"Offset: {spec.page.offset}")  # 自动计算: (page-1) * size
```

---

## 实体查询

### EntitySpecificationBuilder

**核心特性**：默认自动排除软删除记录（`deleted_at IS NULL`）

```python
from bento.persistence.specification import EntitySpecificationBuilder

# 默认：自动排除软删除
spec = EntitySpecificationBuilder().is_active().build()
# SQL: WHERE is_active = true AND deleted_at IS NULL

# 常用方法
spec = (
    EntitySpecificationBuilder()
    .by_id("user-123")                  # ID 查询
    .by_status("active")                # 状态查询
    .is_active()                        # 活跃状态
    .created_after(datetime.now() - timedelta(days=7))  # 时间范围
    .created_in_last_days(30)           # 最近 N 天
    .by_tenant("tenant-123")            # 租户查询
    .build()
)
```

### 常用实体方法

| 方法 | 说明 | SQL |
|------|------|-----|
| `.by_id(id)` | ID 查询 | `WHERE id = ?` |
| `.by_status(status)` | 状态查询 | `WHERE status = ?` |
| `.is_active(True/False)` | 活跃状态 | `WHERE is_active = ?` |
| `.created_after(date)` | 创建时间之后 | `WHERE created_at >= ?` |
| `.created_before(date)` | 创建时间之前 | `WHERE created_at <= ?` |
| `.created_between(start, end)` | 创建时间范围 | `WHERE created_at BETWEEN ? AND ?` |
| `.created_in_last_days(n)` | 最近 N 天 | `WHERE created_at >= NOW() - INTERVAL ? DAYS` |
| `.created_in_month(year, month)` | 指定月份 | `WHERE YEAR(created_at) = ? AND MONTH(created_at) = ?` |
| `.updated_after(date)` | 更新时间之后 | `WHERE updated_at >= ?` |
| `.updated_in_last_days(n)` | 最近 N 天更新 | `WHERE updated_at >= NOW() - INTERVAL ? DAYS` |
| `.by_tenant(tenant_id)` | 租户过滤 | `WHERE tenant_id = ?` |
| `.by_created_by(user_id)` | 创建人 | `WHERE created_by = ?` |
| `.by_updated_by(user_id)` | 更新人 | `WHERE updated_by = ?` |

---

## 聚合根查询

### AggregateSpecificationBuilder

**核心特性**：支持版本控制，**不**应用默认软删除过滤

```python
from bento.persistence.specification import AggregateSpecificationBuilder

# 版本查询
spec = (
    AggregateSpecificationBuilder()
    .with_version(5)              # 精确版本
    .build()
)

# 版本范围
spec = (
    AggregateSpecificationBuilder()
    .with_minimum_version(3)      # version >= 3
    .with_maximum_version(10)     # version <= 10
    .build()
)

# 版本范围
spec = (
    AggregateSpecificationBuilder()
    .with_version_range(1, 10)    # 1 <= version <= 10
    .build()
)
```

### 聚合根专用方法

| 方法 | 说明 | SQL |
|------|------|-----|
| `.by_aggregate_id(id)` | 聚合根 ID | `WHERE id = ?` |
| `.by_aggregate_type(type)` | 聚合类型 | `WHERE aggregate_type = ?` |
| `.with_version(version)` | 精确版本 | `WHERE version = ?` |
| `.with_minimum_version(v)` | 最低版本 | `WHERE version >= ?` |
| `.with_maximum_version(v)` | 最高版本 | `WHERE version <= ?` |
| `.with_version_range(min, max)` | 版本范围 | `WHERE version BETWEEN ? AND ?` |

**注意**：`AggregateSpecificationBuilder` 继承自 `EntitySpecificationBuilder`，因此也可以使用所有实体方法（如 `.is_active()`, `.updated_after()` 等）。

---

## 软删除处理

### 三种查询状态

Bento 使用 `deleted_at` 时间戳字段实现软删除：
- `NULL` = 未删除
- `非 NULL` = 已删除（保存删除时间）

```python
from bento.persistence.specification import EntitySpecificationBuilder

# 1️⃣ 默认：排除软删除（最常见）
spec = EntitySpecificationBuilder().is_active().build()
# SQL: WHERE is_active = true AND deleted_at IS NULL

# 2️⃣ 包含软删除记录
spec = EntitySpecificationBuilder().is_active().include_deleted().build()
# SQL: WHERE is_active = true
# （移除了 deleted_at IS NULL 过滤）

# 3️⃣ 只查询软删除记录
spec = EntitySpecificationBuilder().include_deleted().only_deleted().build()
# SQL: WHERE deleted_at IS NOT NULL
```

### 软删除 API

| 方法 | 行为 | 使用场景 |
|------|------|----------|
| **默认** | 自动添加 `deleted_at IS NULL` | 99% 的业务查询 |
| `.include_deleted()` | 移除默认过滤 | 管理后台、数据恢复 |
| `.only_deleted()` | 添加 `deleted_at IS NOT NULL` | 回收站、审计日志 |

### 完整示例

```python
# 场景1：业务查询（默认）
active_users = await user_repo.find_by_spec(
    EntitySpecificationBuilder()
    .where("status", "=", "active")
    .build()
)
# 自动排除软删除用户

# 场景2：管理后台（包含已删除）
all_users = await user_repo.find_by_spec(
    EntitySpecificationBuilder()
    .where("role", "=", "admin")
    .include_deleted()  # 显式包含已删除用户
    .build()
)

# 场景3：回收站（仅已删除）
deleted_users = await user_repo.find_by_spec(
    EntitySpecificationBuilder()
    .include_deleted()
    .only_deleted()
    .order_by("deleted_at", "desc")
    .build()
)
```

---

## 高级查询

### 使用 Criterion

Criterion 提供更强大的类型安全查询构建：

```python
from bento.persistence.specification import SpecificationBuilder
from bento.persistence.specification.criteria import (
    EqualsCriterion,
    BetweenCriterion,
    InCriterion,
    ContainsCriterion,
    LastNDaysCriterion,
)

# 基础 Criterion
spec = (
    SpecificationBuilder()
    .add_criterion(EqualsCriterion("status", "active"))
    .add_criterion(BetweenCriterion("age", 18, 65))
    .build()
)

# 范围查询
spec = (
    SpecificationBuilder()
    .add_criterion(BetweenCriterion("amount", 100, 1000))
    .add_criterion(InCriterion("category", ["electronics", "books"]))
    .build()
)

# 文本搜索
spec = (
    SpecificationBuilder()
    .add_criterion(ContainsCriterion("name", "John"))      # %John%
    .add_criterion(StartsWithCriterion("email", "admin"))  # admin%
    .add_criterion(EndsWithCriterion("domain", ".com"))    # %.com
    .build()
)

# 时间查询
spec = (
    SpecificationBuilder()
    .add_criterion(LastNDaysCriterion("created_at", 7))   # 最近7天
    .add_criterion(TodayCriterion("updated_at"))          # 今天
    .add_criterion(ThisWeekCriterion("created_at"))       # 本周
    .build()
)
```

### 常用 Criterion

| Criterion | 说明 | SQL |
|-----------|------|-----|
| `EqualsCriterion` | 等于 | `field = value` |
| `NotEqualsCriterion` | 不等于 | `field != value` |
| `GreaterThanCriterion` | 大于 | `field > value` |
| `GreaterEqualCriterion` | 大于等于 | `field >= value` |
| `LessThanCriterion` | 小于 | `field < value` |
| `LessEqualCriterion` | 小于等于 | `field <= value` |
| `BetweenCriterion` | 范围 | `field BETWEEN a AND b` |
| `InCriterion` | 在列表中 | `field IN (...)` |
| `NotInCriterion` | 不在列表中 | `field NOT IN (...)` |
| `LikeCriterion` | 模糊匹配 | `field LIKE pattern` |
| `ILikeCriterion` | 不区分大小写 | `field ILIKE pattern` |
| `ContainsCriterion` | 包含 | `field LIKE %value%` |
| `StartsWithCriterion` | 以...开头 | `field LIKE value%` |
| `EndsWithCriterion` | 以...结尾 | `field LIKE %value` |
| `IsNullCriterion` | 为空 | `field IS NULL` |
| `IsNotNullCriterion` | 不为空 | `field IS NOT NULL` |
| `TodayCriterion` | 今天 | `DATE(field) = CURRENT_DATE` |
| `YesterdayCriterion` | 昨天 | `DATE(field) = CURRENT_DATE - 1` |
| `LastNDaysCriterion` | 最近N天 | `field >= CURRENT_DATE - N` |
| `ThisWeekCriterion` | 本周 | `field >= start_of_week` |
| `ThisMonthCriterion` | 本月 | `field >= start_of_month` |
| `ThisYearCriterion` | 本年 | `field >= start_of_year` |
| `DateRangeCriterion` | 日期范围 | `field BETWEEN a AND b` |
| `OnOrAfterCriterion` | 在...之后 | `field >= date` |
| `OnOrBeforeCriterion` | 在...之前 | `field <= date` |

---

## Criteria 组合

### 逻辑组合器

```python
from bento.persistence.specification.criteria import And, Or

# OR 组合
status_filter = Or(
    EqualsCriterion("status", "active"),
    EqualsCriterion("status", "pending")
)

spec = (
    SpecificationBuilder()
    .add_criterion(status_filter)
    .build()
)
# SQL: WHERE (status = 'active' OR status = 'pending')

# AND 组合
age_and_status = And(
    GreaterEqualCriterion("age", 18),
    EqualsCriterion("status", "active")
)

spec = (
    SpecificationBuilder()
    .add_criterion(age_and_status)
    .build()
)
# SQL: WHERE (age >= 18 AND status = 'active')
```

### 复杂组合

```python
# (status = 'active' OR status = 'pending') AND age >= 18
status_or = Or(
    EqualsCriterion("status", "active"),
    EqualsCriterion("status", "pending")
)
age_filter = GreaterEqualCriterion("age", 18)

spec = (
    SpecificationBuilder()
    .add_criterion(And(status_or, age_filter))
    .build()
)
```

---

## 与 SQLAlchemy 集成

### Repository 中使用

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bento.persistence.specification import EntitySpecificationBuilder

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_spec(self, spec):
        """根据 Specification 查询"""
        stmt = select(User)

        # 应用过滤条件
        for filter in spec.filters:
            if filter.operator == FilterOperator.EQUALS:
                stmt = stmt.where(getattr(User, filter.field) == filter.value)
            elif filter.operator == FilterOperator.GREATER_EQUAL:
                stmt = stmt.where(getattr(User, filter.field) >= filter.value)
            # ... 其他操作符

        # 应用排序
        for sort in spec.sorts:
            col = getattr(User, sort.field)
            stmt = stmt.order_by(col.desc() if sort.direction == SortDirection.DESC else col.asc())

        # 应用分页
        if spec.page:
            stmt = stmt.offset(spec.page.offset).limit(spec.page.size)

        result = await self.session.execute(stmt)
        return result.scalars().all()

# 使用
spec = EntitySpecificationBuilder().is_active().build()
users = await user_repo.find_by_spec(spec)
```

### 通用 Specification Executor

```python
from sqlalchemy import select
from bento.persistence.specification import FilterOperator, SortDirection

class SpecificationExecutor:
    """通用 Specification 执行器"""

    @staticmethod
    def apply_spec(stmt, model, spec):
        """将 Specification 应用到 SQLAlchemy 语句"""
        # 应用过滤
        for filter in spec.filters:
            col = getattr(model, filter.field)

            if filter.operator == FilterOperator.EQUALS:
                stmt = stmt.where(col == filter.value)
            elif filter.operator == FilterOperator.NOT_EQUALS:
                stmt = stmt.where(col != filter.value)
            elif filter.operator == FilterOperator.GREATER_THAN:
                stmt = stmt.where(col > filter.value)
            elif filter.operator == FilterOperator.GREATER_EQUAL:
                stmt = stmt.where(col >= filter.value)
            elif filter.operator == FilterOperator.LESS_THAN:
                stmt = stmt.where(col < filter.value)
            elif filter.operator == FilterOperator.LESS_EQUAL:
                stmt = stmt.where(col <= filter.value)
            elif filter.operator == FilterOperator.IN:
                stmt = stmt.where(col.in_(filter.value))
            elif filter.operator == FilterOperator.NOT_IN:
                stmt = stmt.where(~col.in_(filter.value))
            elif filter.operator == FilterOperator.LIKE:
                stmt = stmt.where(col.like(filter.value))
            elif filter.operator == FilterOperator.ILIKE:
                stmt = stmt.where(col.ilike(filter.value))
            elif filter.operator == FilterOperator.IS_NULL:
                stmt = stmt.where(col.is_(None))
            elif filter.operator == FilterOperator.IS_NOT_NULL:
                stmt = stmt.where(col.is_not(None))
            elif filter.operator == FilterOperator.BETWEEN:
                stmt = stmt.where(col.between(filter.value["start"], filter.value["end"]))

        # 应用排序
        for sort in spec.sorts:
            col = getattr(model, sort.field)
            if sort.direction == SortDirection.DESC:
                stmt = stmt.order_by(col.desc())
            else:
                stmt = stmt.order_by(col.asc())

        # 应用分页
        if spec.page:
            stmt = stmt.offset(spec.page.offset).limit(spec.page.size)

        return stmt

# 使用
stmt = select(User)
spec = EntitySpecificationBuilder().is_active().order_by("name").build()
stmt = SpecificationExecutor.apply_spec(stmt, User, spec)
```

---

## 最佳实践

### 1. 创建可重用的 Specification 类

**推荐**：将常用查询封装为类

```python
class ActiveUsersSpec:
    """活跃用户规格"""

    @staticmethod
    def build(min_age: int = 18):
        return (
            EntitySpecificationBuilder()
            .is_active()
            .where("age", ">=", min_age)
            .order_by("created_at", "desc")
            .build()
        )

class RecentOrdersSpec:
    """最近订单规格"""

    @staticmethod
    def build(days: int = 7):
        return (
            EntitySpecificationBuilder()
            .where("status", "in", ["pending", "processing"])
            .created_in_last_days(days)
            .order_by("created_at", "desc")
            .build()
        )

# 使用
active_users = await user_repo.find_by_spec(ActiveUsersSpec.build())
recent_orders = await order_repo.find_by_spec(RecentOrdersSpec.build(days=30))
```

### 2. 参数化查询

**推荐**：构建动态查询函数

```python
def build_user_search_spec(
    status: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    tenant_id: str | None = None,
    page: int = 1,
    size: int = 20,
):
    """构建用户搜索规格"""
    builder = EntitySpecificationBuilder()

    if status:
        builder = builder.where("status", "=", status)

    if min_age is not None:
        builder = builder.where("age", ">=", min_age)

    if max_age is not None:
        builder = builder.where("age", "<=", max_age)

    if tenant_id:
        builder = builder.by_tenant(tenant_id)

    return (
        builder
        .order_by("created_at", "desc")
        .paginate(page=page, size=size)
        .build()
    )

# 使用
spec = build_user_search_spec(
    status="active",
    min_age=18,
    max_age=65,
    page=1,
    size=20
)
```

### 3. 在查询服务中使用

**推荐**：在 CQRS 的查询服务中使用 Specification

```python
class OrderQueryService:
    """订单查询服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_orders(
        self,
        status: list[str] | None = None,
        customer_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        size: int = 20,
    ):
        """搜索订单"""
        builder = EntitySpecificationBuilder()

        if status:
            builder = builder.where("status", "in", status)

        if customer_id:
            builder = builder.where("customer_id", "=", customer_id)

        if date_from:
            builder = builder.created_after(date_from)

        if date_to:
            builder = builder.created_before(date_to)

        spec = builder.order_by("created_at", "desc").paginate(page, size).build()

        # 执行查询
        stmt = SpecificationExecutor.apply_spec(select(Order), Order, spec)
        result = await self.session.execute(stmt)
        orders = result.scalars().all()

        # 返回分页结果
        return {
            "items": orders,
            "page": page,
            "size": size,
            "total": await self._count_orders(spec),
        }
```

### 4. 单元测试

**推荐**：独立测试 Specification 逻辑

```python
def test_active_users_spec():
    """测试活跃用户规格"""
    spec = ActiveUsersSpec.build(min_age=21)

    # 验证过滤条件
    assert len(spec.filters) == 3
    assert spec.filters[0].field == "deleted_at"  # 默认软删除过滤
    assert spec.filters[1].field == "is_active"
    assert spec.filters[2].field == "age"
    assert spec.filters[2].value == 21

    # 验证排序
    assert len(spec.sorts) == 1
    assert spec.sorts[0].field == "created_at"
    assert spec.sorts[0].direction == SortDirection.DESC

def test_soft_delete_behavior():
    """测试软删除行为"""
    # 默认排除软删除
    spec1 = EntitySpecificationBuilder().build()
    assert spec1.filters[0].field == "deleted_at"
    assert spec1.filters[0].operator == FilterOperator.IS_NULL

    # 包含软删除
    spec2 = EntitySpecificationBuilder().include_deleted().build()
    assert len(spec2.filters) == 0

    # 只查询软删除
    spec3 = EntitySpecificationBuilder().include_deleted().only_deleted().build()
    assert spec3.filters[0].field == "deleted_at"
    assert spec3.filters[0].operator == FilterOperator.IS_NOT_NULL
```

### 5. 避免过度复杂

**不推荐**：在一个 Specification 中塞入过多逻辑

```python
# ❌ 过于复杂
spec = (
    EntitySpecificationBuilder()
    .where("field1", "=", value1)
    .where("field2", "=", value2)
    .where("field3", "=", value3)
    # ... 10+ 条件
    .build()
)
```

**推荐**：拆分为多个简单的 Specification 或使用参数化函数

```python
# ✅ 清晰简洁
class ComplexSearchSpec:
    @staticmethod
    def build(filters: dict):
        builder = EntitySpecificationBuilder()

        for key, value in filters.items():
            if value is not None:
                builder = builder.where(key, "=", value)

        return builder.build()
```

### 6. 类型安全

**推荐**：使用 Criterion 获得更好的类型安全

```python
# ✅ 类型安全
from bento.persistence.specification.criteria import (
    EqualsCriterion,
    BetweenCriterion,
)

spec = (
    SpecificationBuilder()
    .add_criterion(EqualsCriterion("status", "active"))  # 明确类型
    .add_criterion(BetweenCriterion("age", 18, 65))      # 参数清晰
    .build()
)

# vs. 字符串操作符（较弱的类型检查）
spec = (
    SpecificationBuilder()
    .where("status", "=", "active")  # 操作符是字符串
    .where("age", "between", {"start": 18, "end": 65})  # 容易出错
    .build()
)
```

### 7. 软删除策略

**原则**：明确软删除行为

```python
# ✅ 业务查询：使用 EntitySpecificationBuilder（自动排除软删除）
active_orders = await order_repo.find_by_spec(
    EntitySpecificationBuilder()
    .where("status", "=", "active")
    .build()
)

# ✅ 管理查询：显式包含软删除
all_orders = await order_repo.find_by_spec(
    EntitySpecificationBuilder()
    .where("customer_id", "=", customer_id)
    .include_deleted()  # 明确意图
    .build()
)

# ✅ 通用查询：无特殊处理
stats = await analytics_repo.find_by_spec(
    SpecificationBuilder()  # 不使用 EntitySpecificationBuilder
    .where("type", "=", "report")
    .build()
)
```

---

## 故障排查

### 问题 1：软删除记录未被过滤

**症状**：
```python
spec = EntitySpecificationBuilder().is_active().build()
# 返回了已删除的记录
```

**原因**：检查是否正确使用了 `EntitySpecificationBuilder`

**解决**：
```python
# ✅ 确保使用 EntitySpecificationBuilder
from bento.persistence.specification import EntitySpecificationBuilder

spec = EntitySpecificationBuilder().is_active().build()
# 自动添加 deleted_at IS NULL

# 检查过滤条件
assert spec.filters[0].field == "deleted_at"
```

### 问题 2：分页计算错误

**症状**：
```python
spec = builder.paginate(page=2, size=20).build()
# offset 不正确
```

**原因**：页码从 1 开始，而不是 0

**解决**：
```python
# ✅ 页码从 1 开始
spec = builder.paginate(page=1, size=20).build()  # offset = 0
spec = builder.paginate(page=2, size=20).build()  # offset = 20

# 验证
print(f"Offset: {spec.page.offset}")  # (page - 1) * size
```

### 问题 3：操作符不匹配

**症状**：
```python
spec = builder.where("age", "between", [18, 65]).build()
# SQL 执行错误
```

**原因**：`between` 操作符需要特定的值格式

**解决**：
```python
# ❌ 错误：列表格式
spec = builder.where("age", "between", [18, 65]).build()

# ✅ 正确：字典格式
spec = builder.where("age", "between", {"start": 18, "end": 65}).build()

# ✅ 或使用 Criterion
from bento.persistence.specification.criteria import BetweenCriterion
spec = builder.add_criterion(BetweenCriterion("age", 18, 65)).build()
```

### 问题 4：聚合根查询包含软删除过滤

**症状**：
```python
spec = AggregateSpecificationBuilder().with_version(5).build()
# 返回的记录少于预期（被软删除过滤了）
```

**原因**：错误地期望聚合根查询有软删除过滤

**解决**：
```python
# ✅ AggregateSpecificationBuilder 不应用软删除过滤
spec = AggregateSpecificationBuilder().with_version(5).build()
# 不会添加 deleted_at IS NULL

# 如果聚合根确实需要软删除，手动添加：
spec = (
    AggregateSpecificationBuilder()
    .with_version(5)
    .where("deleted_at", "is null", None)
    .build()
)
```

### 问题 5：Criterion 未生效

**症状**：
```python
criterion = EqualsCriterion("status", "active")
spec = builder.add_criterion(criterion.to_filter()).build()  # 错误！
```

**原因**：不应该调用 `.to_filter()`

**解决**：
```python
# ❌ 错误：手动转换
spec = builder.add_criterion(criterion.to_filter()).build()

# ✅ 正确：直接添加 Criterion
spec = builder.add_criterion(criterion).build()

# Builder 会自动调用 to_filter()
```

### 问题 6：类型检查错误

**症状**：
```python
# 类型检查器报错
spec = builder.where("age", ">", "18").build()  # "18" 是字符串
```

**原因**：值类型不匹配

**解决**：
```python
# ✅ 使用正确的类型
spec = builder.where("age", ">", 18).build()  # 整数

# ✅ 或明确转换
age_str = "18"
spec = builder.where("age", ">", int(age_str)).build()
```

---

## 快速参考

### 核心导入

```python
from bento.persistence.specification import (
    SpecificationBuilder,
    EntitySpecificationBuilder,
    AggregateSpecificationBuilder,
    FilterOperator,
    SortDirection,
)
from bento.persistence.specification.criteria import (
    EqualsCriterion,
    BetweenCriterion,
    InCriterion,
    ContainsCriterion,
    And,
    Or,
)
```

### 链式调用顺序

```python
spec = (
    EntitySpecificationBuilder()
    # 1. 过滤条件
    .where("field", "op", value)
    .add_criterion(criterion)
    .is_active()
    .created_in_last_days(7)
    # 2. 软删除控制（可选）
    .include_deleted()
    .only_deleted()
    # 3. 排序
    .order_by("field", "direction")
    # 4. 分页
    .paginate(page=1, size=20)
    # 5. 构建
    .build()
)
```

### 三种 Builder 对比

| 特性 | SpecificationBuilder | EntitySpecificationBuilder | AggregateSpecificationBuilder |
|------|---------------------|---------------------------|------------------------------|
| 软删除默认 | ❌ | ✅ | ❌ |
| 实体方法 | ❌ | ✅ | ✅ (继承) |
| 版本控制 | ❌ | ❌ | ✅ |
| 适用场景 | 通用查询 | 业务实体 | DDD 聚合 |

---

## 相关文档

- [Specification Pattern 指南](../guides/SPECIFICATION_PATTERN.md) - 设计原理和模式详解
- [软删除默认行为](../../SOFT_DELETE_DEFAULT_BEHAVIOR.md) - 软删除设计决策
- [数据库基础设施](./DATABASE_USAGE.md) - 数据库配置和使用
- [Repository 模式](../guides/REPOSITORY_PATTERN.md) - 仓储模式最佳实践

---

**最后更新**: 2025-11-06
**维护者**: Bento Framework Team

