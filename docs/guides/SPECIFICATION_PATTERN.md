# Specification Pattern 使用指南

## 概述

Specification Pattern（规格模式）是一种企业级设计模式，用于封装查询逻辑，使其可重用、可组合且易于测试。Bento框架提供了完整的Specification实现，支持：

- 🔍 类型安全的查询构建
- 🧩 可组合的过滤条件
- 📦 可重用的查询规格
- 🎯 清晰的查询意图
- ✅ 易于单元测试

## 核心概念

### 1. 基础组件

```python
from bento.persistence.specification import (
    SpecificationBuilder,      # 通用规格构建器
    EntitySpecificationBuilder, # 实体规格构建器
    AggregateSpecificationBuilder,  # 聚合规格构建器
    FilterOperator,              # 过滤操作符
    SortDirection,               # 排序方向
)
```

### 2. Criteria（条件）

Criteria是构建Specification的基础单元，代表单一的查询条件：

```python
from bento.persistence.specification.criteria import (
    # 比较条件
    EqualsCriterion,
    NotEqualsCriterion,
    GreaterThanCriterion,
    LessThanCriterion,
    BetweenCriterion,
    InCriterion,

    # 文本条件
    LikeCriterion,
    ContainsCriterion,
    StartsWithCriterion,
    EndsWithCriterion,

    # 时间条件
    TodayCriterion,
    YesterdayCriterion,
    LastNDaysCriterion,

    # 逻辑组合
    And,
    Or,
)
```

## 使用示例

### 示例1：简单过滤

```python
from bento.persistence.specification import SpecificationBuilder
from bento.persistence.specification.criteria import EqualsCriterion

# 构建规格：查询状态为"active"的记录
spec = (
    SpecificationBuilder()
    .add_filter(EqualsCriterion("status", "active").to_filter())
    .build()
)
```

### 示例2：多条件查询

```python
from bento.persistence.specification.criteria import (
    EqualsCriterion,
    GreaterEqualCriterion,
    LessThanCriterion,
)

# 查询：status=active AND age >= 18 AND age < 65
spec = (
    SpecificationBuilder()
    .add_filter(EqualsCriterion("status", "active").to_filter())
    .add_filter(GreaterEqualCriterion("age", 18).to_filter())
    .add_filter(LessThanCriterion("age", 65).to_filter())
    .build()
)
```

### 示例3：排序和分页

```python
from bento.persistence.specification import SortDirection

# 按创建时间降序，分页查询
spec = (
    SpecificationBuilder()
    .where("status", "=", "active")
    .order_by("created_at", SortDirection.DESC)
    .paginate(page=1, page_size=20)
    .build()
)
```

### 示例4：复杂查询（Range + 文本搜索）

```python
from bento.persistence.specification.criteria import (
    BetweenCriterion,
    ContainsCriterion,
)

# 金额范围 + 名称搜索
spec = (
    SpecificationBuilder()
    .add_filter(BetweenCriterion("amount", 100, 1000).to_filter())
    .add_filter(ContainsCriterion("name", "Premium").to_filter())
    .order_by("amount", SortDirection.DESC)
    .limit(50)
    .build()
)
```

### 示例5：日期范围查询

```python
from bento.persistence.specification.criteria import (
    LastNDaysCriterion,
    TodayCriterion,
)

# 最近7天的订单
spec = (
    SpecificationBuilder()
    .add_filter(LastNDaysCriterion("created_at", 7).to_filter())
    .order_by("created_at", SortDirection.DESC)
    .build()
)

# 今天的订单
today_spec = (
    SpecificationBuilder()
    .add_filter(TodayCriterion("created_at").to_filter())
    .build()
)
```

### 示例6：逻辑组合（AND/OR）

```python
from bento.persistence.specification.criteria import And, Or, EqualsCriterion

# (status = "active" OR status = "pending") AND priority = "high"
status_criteria = Or(
    EqualsCriterion("status", "active"),
    EqualsCriterion("status", "pending")
)
priority_criterion = EqualsCriterion("priority", "high")

combined = And(status_criteria, priority_criterion)
```

## 在Query Service中使用

### 完整示例：Order Query Service

```python
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bento.persistence.specification import (
    SpecificationBuilder,
    SortDirection,
)
from bento.persistence.specification.criteria import (
    EqualsCriterion,
    BetweenCriterion,
    GreaterEqualCriterion,
)


class OrderQueryService:
    """订单查询服务，使用 Specification 模式"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_orders(
        self,
        *,
        customer_id: str | None = None,
        status: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """使用Specification模式查询订单"""

        # 1. 构建Specification
        builder = SpecificationBuilder()

        if customer_id:
            builder = builder.add_filter(
                EqualsCriterion("customer_id", customer_id).to_filter()
            )

        if status:
            builder = builder.add_filter(
                EqualsCriterion("status", status).to_filter()
            )

        if min_amount and max_amount:
            builder = builder.add_filter(
                BetweenCriterion("total_amount", min_amount, max_amount).to_filter()
            )
        elif min_amount:
            builder = builder.add_filter(
                GreaterEqualCriterion("total_amount", min_amount).to_filter()
            )

        # 添加排序和分页
        spec = (
            builder
            .order_by("created_at", SortDirection.DESC)
            .paginate(page=page, page_size=page_size)
            .build()
        )

        # 2. 将Specification应用到SQLAlchemy查询
        stmt = self._apply_spec_to_query(select(OrderModel), spec)

        # 3. 执行查询
        result = await self._session.execute(stmt)
        orders = result.scalars().all()

        # 4. 获取总数（用于分页）
        total = await self._count_with_spec(OrderModel, spec)

        return {
            "items": [self._to_dict(order) for order in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _apply_spec_to_query(self, stmt, spec):
        """将Specification应用到SQLAlchemy查询"""
        # 应用过滤条件
        for filter in spec.filters:
            stmt = self._apply_filter(stmt, filter)

        # 应用排序
        for sort in spec.sorts:
            if sort.direction == SortDirection.DESC:
                stmt = stmt.order_by(getattr(OrderModel, sort.field).desc())
            else:
                stmt = stmt.order_by(getattr(OrderModel, sort.field).asc())

        # 应用分页
        if spec.page:
            offset = (spec.page.page - 1) * spec.page.page_size
            stmt = stmt.limit(spec.page.page_size).offset(offset)

        return stmt
```

## Entity和Aggregate专用构建器

### EntitySpecificationBuilder

用于查询实体，提供软删除、审计字段等常用过滤。

**重要特性：软删除默认行为**

`EntitySpecificationBuilder` **默认会自动排除软删除的记录** (deleted_at IS NULL)。
这是一个"安全优先"的设计，避免意外查询到已删除的数据。

```python
from bento.persistence.specification import EntitySpecificationBuilder
from datetime import datetime, timedelta

# 默认行为：自动排除软删除记录
spec = EntitySpecificationBuilder().is_active().build()
# 生成 SQL: WHERE is_active = true AND deleted_at IS NULL

# 如需包含软删除记录，显式调用 include_deleted()
spec = EntitySpecificationBuilder().is_active().include_deleted().build()
# 生成 SQL: WHERE is_active = true

# 只查询软删除记录
spec = EntitySpecificationBuilder().include_deleted().only_deleted().build()
# 生成 SQL: WHERE deleted_at IS NOT NULL
```

**常用方法：**

```python
# 查询未删除的、最近创建的记录（默认排除软删除）
spec = (
    EntitySpecificationBuilder()
    .created_after(datetime.now() - timedelta(days=7))
    .order_by("created_at", SortDirection.DESC)
    .build()
)
```

### AggregateSpecificationBuilder

用于查询聚合根，支持版本控制等：

```python
from bento.persistence.specification import AggregateSpecificationBuilder

# 查询特定版本的聚合
spec = (
    AggregateSpecificationBuilder()
    .with_version(5)  # version = 5
    .by_aggregate_id(aggregate_id)
    .build()
)

# 查询最低版本的聚合
spec = (
    AggregateSpecificationBuilder()
    .with_minimum_version(3)  # version >= 3
    .order_by("version", SortDirection.ASC)
    .build()
)
```

## 可重用的Specification

### 创建自定义Specification类

```python
from bento.persistence.specification import SpecificationBuilder
from bento.persistence.specification.criteria import (
    EqualsCriterion,
    GreaterEqualCriterion,
    LastNDaysCriterion,
)


class ActiveOrdersSpec:
    """可重用的"活跃订单"规格"""

    @staticmethod
    def build():
        return (
            SpecificationBuilder()
            .add_filter(EqualsCriterion("status", "active").to_filter())
            .add_filter(GreaterEqualCriterion("total_amount", 0).to_filter())
            .build()
        )


class RecentOrdersSpec:
    """可重用的"最近订单"规格"""

    @staticmethod
    def build(days: int = 7):
        return (
            SpecificationBuilder()
            .add_filter(LastNDaysCriterion("created_at", days).to_filter())
            .order_by("created_at", SortDirection.DESC)
            .build()
        )


# 使用
active_spec = ActiveOrdersSpec.build()
recent_spec = RecentOrdersSpec.build(days=30)
```

## 测试Specification

Specification的一个重要优势是易于测试：

```python
import pytest
from bento.persistence.specification import SpecificationBuilder, FilterOperator
from bento.persistence.specification.criteria import EqualsCriterion


def test_active_orders_spec():
    """测试活跃订单规格"""
    spec = (
        SpecificationBuilder()
        .add_filter(EqualsCriterion("status", "active").to_filter())
        .build()
    )

    # 验证规格
    assert len(spec.filters) == 1
    assert spec.filters[0].field == "status"
    assert spec.filters[0].operator == FilterOperator.EQUALS
    assert spec.filters[0].value == "active"


def test_pagination_spec():
    """测试分页规格"""
    spec = (
        SpecificationBuilder()
        .paginate(page=2, page_size=20)
        .build()
    )

    assert spec.page is not None
    assert spec.page.page == 2
    assert spec.page.page_size == 20
```

## 最佳实践

### ✅ DO

1. **使用Fluent API**：链式调用使代码更易读
   ```python
   spec = (
       SpecificationBuilder()
       .where("status", "=", "active")
       .order_by("created_at", SortDirection.DESC)
       .paginate(page=1, page_size=20)
       .build()
   )
   ```

2. **创建可重用的Specification类**：封装复杂查询逻辑
   ```python
   class PremiumCustomersSpec:
       @staticmethod
       def build():
           return SpecificationBuilder()...
   ```

3. **在Query Service中使用**：保持查询逻辑的一致性

4. **为Specification编写测试**：验证查询逻辑正确性

### ❌ DON'T

1. **不要在Domain层直接使用SQLAlchemy**：使用Specification抽象

2. **不要重复构建相同的查询逻辑**：创建可重用的Specification

3. **不要在Specification中包含业务逻辑**：Specification只负责查询构建

## 进阶用法

### 动态查询构建

```python
def build_order_search_spec(
    filters: dict[str, Any],
    page: int = 1,
    page_size: int = 20,
):
    """根据动态参数构建查询规格"""
    builder = SpecificationBuilder()

    # 动态添加过滤条件
    for key, value in filters.items():
        if value is not None:
            if isinstance(value, list):
                builder = builder.where(key, "in", value)
            else:
                builder = builder.where(key, "=", value)

    return builder.paginate(page, page_size).build()
```

### 组合多个Specification

```python
# 虽然Specification本身不直接支持组合，
# 但可以通过构建器的add_filter方法组合多个条件

base_spec = ActiveOrdersSpec.build()
recent_spec = RecentOrdersSpec.build()

# 合并两个规格的过滤条件
builder = SpecificationBuilder()
for filter in base_spec.filters:
    builder = builder.add_filter(filter)
for filter in recent_spec.filters:
    builder = builder.add_filter(filter)

combined_spec = builder.build()
```

## 小结

Specification模式提供了：

- ✅ **类型安全**：编译时检查，减少运行时错误
- ✅ **可重用**：封装查询逻辑，避免重复代码
- ✅ **可测试**：独立于数据库，易于单元测试
- ✅ **可组合**：灵活组合多个查询条件
- ✅ **可读性**：清晰表达查询意图

在Bento框架中，建议在所有Query Service中使用Specification模式来构建复杂查询，这将使代码更加清晰、可维护和可测试。

