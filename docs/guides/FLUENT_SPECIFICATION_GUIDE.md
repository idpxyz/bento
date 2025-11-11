# FluentSpecificationBuilder 使用指南

## 概述

`FluentSpecificationBuilder` 是 Bento 框架中用于构建复杂查询规格的流式 API，它提供了一种直观、类型安全的方式来构建数据库查询条件。

## 核心优势

### 1. **可读性强**
```python
# 传统方式
spec = SpecificationBuilder()
spec.add_criterion(EqualsCriterion("status", "active"))
spec.add_criterion(GreaterThanCriterion("amount", 100))
spec.add_sort_order(SortOrder("created_at", False))
spec.set_page(PageParams(page=1, size=20))

# FluentBuilder 方式
spec = (
    FluentSpecificationBuilder()
    .equals("status", "active")
    .greater_than("amount", 100)
    .order_by("created_at", descending=True)
    .paginate(page=1, size=20)
    .build()
)
```

### 2. **类型安全**
- IDE 自动补全
- 类型检查
- 方法链式调用

### 3. **默认智能处理**
- 自动过滤软删除记录（`deleted_at IS NULL`）
- 可显式控制软删除行为

## 快速开始

### 基础用法

```python
from bento.persistence.specification.builder import FluentSpecificationBuilder

# 简单查询
spec = (
    FluentSpecificationBuilder()
    .equals("status", "active")
    .build()
)

# 链式调用多个条件
spec = (
    FluentSpecificationBuilder()
    .equals("customer_id", "cust-001")
    .greater_than_or_equal("total_amount", 100.0)
    .less_than("total_amount", 1000.0)
    .order_by("created_at", descending=True)
    .paginate(page=1, size=20)
    .build()
)
```

## 完整 API 参考

### 比较操作符

#### `equals(field, value)`
精确匹配

```python
builder.equals("status", "paid")
# SQL: WHERE status = 'paid'
```

#### `not_equals(field, value)`
不等于

```python
builder.not_equals("status", "cancelled")
# SQL: WHERE status != 'cancelled'
```

#### `greater_than(field, value)`
大于

```python
builder.greater_than("amount", 100)
# SQL: WHERE amount > 100
```

#### `greater_than_or_equal(field, value)`
大于等于

```python
builder.greater_than_or_equal("amount", 100)
# SQL: WHERE amount >= 100
```

#### `less_than(field, value)`
小于

```python
builder.less_than("amount", 1000)
# SQL: WHERE amount < 1000
```

#### `less_than_or_equal(field, value)`
小于等于

```python
builder.less_than_or_equal("amount", 1000)
# SQL: WHERE amount <= 1000
```

#### `in_(field, values)`
包含于列表

```python
builder.in_("status", ["pending", "paid", "shipped"])
# SQL: WHERE status IN ('pending', 'paid', 'shipped')
```

#### `not_in(field, values)`
不包含于列表

```python
builder.not_in("status", ["cancelled", "refunded"])
# SQL: WHERE status NOT IN ('cancelled', 'refunded')
```

#### `like(field, pattern)`
模糊匹配

```python
builder.like("product_name", "%iPhone%")
# SQL: WHERE product_name LIKE '%iPhone%'
```

#### `is_null(field)`
字段为空

```python
builder.is_null("cancelled_at")
# SQL: WHERE cancelled_at IS NULL
```

#### `is_not_null(field)`
字段不为空

```python
builder.is_not_null("paid_at")
# SQL: WHERE paid_at IS NOT NULL
```

### 逻辑操作符

#### 默认 AND 行为
多个条件默认使用 AND 连接

```python
builder.equals("status", "active").greater_than("amount", 100)
# SQL: WHERE status = 'active' AND amount > 100
```

#### 使用 IN 实现 OR 逻辑
对于单字段的多值匹配，使用 `in_()` 方法

```python
builder.in_("status", ["pending", "processing", "shipped"])
# SQL: WHERE status IN ('pending', 'processing', 'shipped')
# 等价于: status = 'pending' OR status = 'processing' OR status = 'shipped'
```

#### 复杂 OR 逻辑
对于复杂的 OR 组合，使用传统 Specification 的 `or_()` 方法

```python
# 先分别构建子规格
spec1 = FluentSpecificationBuilder(OrderModel).equals("status", "paid").build()
spec2 = FluentSpecificationBuilder(OrderModel).equals("status", "shipped").build()

# 使用 Specification 的 or_ 方法组合
combined_spec = spec1.or_(spec2)
# SQL: WHERE (status = 'paid') OR (status = 'shipped')
```

### 排序

#### `order_by(field, descending=False)`
添加排序

```python
# 升序
builder.order_by("created_at")
# SQL: ORDER BY created_at ASC

# 降序
builder.order_by("created_at", descending=True)
# SQL: ORDER BY created_at DESC

# 多字段排序
builder.order_by("status").order_by("created_at", descending=True)
# SQL: ORDER BY status ASC, created_at DESC
```

### 分页

#### 方式 1: `paginate(page, size)`
**推荐方式** - 符合 Bento 风格

```python
builder.paginate(page=1, size=20)
# 第 1 页，每页 20 条
```

#### 方式 2: `limit(n)` + `offset(n)`
灵活控制

```python
builder.limit(20).offset(0)
# 等同于 paginate(page=1, size=20)

builder.limit(10).offset(50)
# 跳过前 50 条，取 10 条
```

### 软删除控制

#### 默认行为
**自动过滤软删除记录**

```python
builder.equals("status", "active").build()
# SQL: WHERE status = 'active' AND deleted_at IS NULL
```

#### `include_deleted()`
包含已删除记录

```python
builder.equals("status", "active").include_deleted().build()
# SQL: WHERE status = 'active'
# (不过滤 deleted_at)
```

#### `only_deleted()`
仅查询已删除记录

```python
builder.only_deleted().build()
# SQL: WHERE deleted_at IS NOT NULL
```

### 构建规格

#### `build()`
构建最终的 `CompositeSpecification`

```python
spec = builder.build()
# 返回 CompositeSpecification 对象
```

## 实战示例

### 示例 1: 电商订单查询

```python
from bento.persistence.specification.builder import FluentSpecificationBuilder

def list_orders_with_specification(
    customer_id: str | None = None,
    status: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """使用 FluentBuilder 构建订单查询"""
    builder = FluentSpecificationBuilder()

    # 动态添加条件
    if customer_id:
        builder.equals("customer_id", customer_id)

    if status:
        builder.equals("status", status)

    if min_amount is not None:
        builder.greater_than_or_equal("total_amount", min_amount)

    if max_amount is not None:
        builder.less_than_or_equal("total_amount", max_amount)

    # 排序和分页
    builder.order_by("created_at", descending=True)
    builder.paginate(page=page, size=min(page_size, 100))

    spec = builder.build()

    # 使用 Repository 执行查询
    return await repository.find_by_specification(spec)
```

### 示例 2: 复杂查询条件

```python
# 查询：(状态=已支付 OR 状态=已发货) AND 金额>1000 AND 未删除
spec = (
    FluentSpecificationBuilder(OrderModel)
    .in_("status", ["paid", "shipped"])  # 使用 IN 实现 OR 逻辑
    .greater_than("total_amount", 1000)
    .order_by("paid_at", descending=True)
    .paginate(page=1, size=50)
    .build()
)
```

### 示例 3: 软删除场景

```python
# 场景 A: 只查询活跃订单（默认）
active_orders_spec = (
    FluentSpecificationBuilder()
    .equals("status", "active")
    .build()
)
# SQL: WHERE status = 'active' AND deleted_at IS NULL

# 场景 B: 查询所有订单（包括已删除）
all_orders_spec = (
    FluentSpecificationBuilder()
    .equals("customer_id", "cust-001")
    .include_deleted()
    .build()
)
# SQL: WHERE customer_id = 'cust-001'

# 场景 C: 仅查询已删除订单
deleted_orders_spec = (
    FluentSpecificationBuilder()
    .only_deleted()
    .order_by("deleted_at", descending=True)
    .paginate(page=1, size=20)
    .build()
)
# SQL: WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT 20 OFFSET 0
```

### 示例 4: 搜索功能

```python
def search_products(keyword: str, category: str | None, page: int):
    """产品搜索"""
    builder = (
        FluentSpecificationBuilder()
        .like("name", f"%{keyword}%")
    )

    if category:
        builder.equals("category", category)

    spec = builder.order_by("name").paginate(page=page, size=50).build()

    return await product_repository.find_by_specification(spec)
```

### 示例 5: 数据分析查询

```python
def get_high_value_customers(min_order_count: int, min_total_spent: float):
    """查询高价值客户"""
    spec = (
        FluentSpecificationBuilder()
        .greater_than_or_equal("order_count", min_order_count)
        .greater_than_or_equal("total_spent", min_total_spent)
        .is_not_null("email")  # 有邮箱的客户
        .order_by("total_spent", descending=True)
        .limit(100)  # 只取前 100 名
        .build()
    )

    return await customer_repository.find_by_specification(spec)
```

## 与传统 SpecificationBuilder 对比

### 传统方式
```python
from bento.persistence.specification.builder import SpecificationBuilder
from bento.persistence.specification.core import (
    EqualsCriterion,
    GreaterThanCriterion,
    SortOrder,
    PageParams,
)

# 需要手动创建各种 Criterion 对象
builder = SpecificationBuilder()
builder.add_criterion(EqualsCriterion("customer_id", "cust-001"))
builder.add_criterion(GreaterThanCriterion("amount", 100))
builder.add_sort_order(SortOrder("created_at", False))
builder.set_page(PageParams(page=1, size=20))
spec = builder.build()
```

### FluentBuilder 方式
```python
from bento.persistence.specification.builder import FluentSpecificationBuilder

# 流式 API，直观易读
spec = (
    FluentSpecificationBuilder()
    .equals("customer_id", "cust-001")
    .greater_than("amount", 100)
    .order_by("created_at", descending=True)
    .paginate(page=1, size=20)
    .build()
)
```

**代码行数减少 60%+，可读性显著提升！**

## 最佳实践

### ✅ DO

1. **使用方法链式调用**
```python
spec = (
    FluentSpecificationBuilder()
    .equals("status", "active")
    .greater_than("amount", 100)
    .order_by("created_at", descending=True)
    .paginate(page=1, size=20)
    .build()
)
```

2. **动态构建查询**
```python
builder = FluentSpecificationBuilder()

if customer_id:
    builder.equals("customer_id", customer_id)

if min_amount:
    builder.greater_than_or_equal("amount", min_amount)

spec = builder.build()
```

3. **使用 `paginate()` 代替 `limit/offset`**（推荐）
```python
# 推荐
builder.paginate(page=1, size=20)

# 也可以（灵活场景）
builder.limit(20).offset(0)
```

4. **显式控制软删除**
```python
# 需要包含已删除数据时，明确声明
builder.include_deleted()
```

5. **使用 IN 实现单字段多值匹配**
```python
# 推荐：使用 IN
builder.in_("status", ["paid", "shipped", "delivered"])

# 不推荐：手动构建多个 OR（FluentBuilder 不支持 or_() 方法）
```

### ❌ DON'T

1. **不要混用 FluentBuilder 和传统 Criterion**
```python
# ❌ 不要这样
builder = FluentSpecificationBuilder(OrderModel)
builder.equals("status", "active")
builder.add_criterion(EqualsCriterion("amount", 100))  # 不一致
```

2. **不要忘记调用 `build()`**
```python
# ❌ 错误
spec = FluentSpecificationBuilder(OrderModel).equals("status", "active")
await repo.find_by_specification(spec)  # spec 不是 Specification 对象

# ✅ 正确
spec = FluentSpecificationBuilder(OrderModel).equals("status", "active").build()
await repo.find_by_specification(spec)
```

3. **不要尝试使用不存在的 `or_()` / `and_()` 方法**
```python
# ❌ FluentBuilder 不支持链式 OR
builder.equals("a", 1).or_().equals("b", 2)  # AttributeError

# ✅ 使用 IN 或组合多个 Specification
# 方式 1: 使用 IN（推荐）
builder.in_("status", ["paid", "shipped"])

# 方式 2: 组合 Specification
spec1 = FluentSpecificationBuilder(OrderModel).equals("a", 1).build()
spec2 = FluentSpecificationBuilder(OrderModel).equals("b", 2).build()
combined = spec1.or_(spec2)
```

## 性能考虑

### 1. **分页限制**
```python
# 限制单次查询数量，防止内存溢出
max_page_size = 100
builder.paginate(page=page, size=min(page_size, max_page_size))
```

### 2. **索引优化**
确保查询的字段有数据库索引

```python
# 如果经常按 customer_id + created_at 查询
builder.equals("customer_id", cid).order_by("created_at", descending=True)

# 数据库应有复合索引：CREATE INDEX idx_customer_created ON orders(customer_id, created_at DESC)
```

### 3. **避免过度过滤**
```python
# ❌ 过多条件可能导致全表扫描
builder.like("name", "%x%").like("desc", "%y%").like("tags", "%z%")

# ✅ 考虑全文搜索或 ElasticSearch
```

## 与 Repository 集成

```python
from bento.persistence.specification.builder import FluentSpecificationBuilder
from applications.ecommerce.modules.order.adapters import OrderRepositoryWithInterceptors

class OrderQueryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = OrderRepositoryWithInterceptors(session, actor="system")

    async def list_orders(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """列出订单"""
        builder = FluentSpecificationBuilder()

        if customer_id:
            builder.equals("customer_id", customer_id)

        if status:
            builder.equals("status", status)

        spec = (
            builder
            .order_by("created_at", descending=True)
            .paginate(page=page, size=page_size)
            .build()
        )

        # 使用 Repository 执行查询
        result = await self.repository.find_by_specification(spec)

        return {
            "items": [self._to_dict(order) for order in result.items],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }
```

## 测试

```python
import pytest
from bento.persistence.specification.builder import FluentSpecificationBuilder

def test_fluent_builder_basic():
    """测试基础构建"""
    spec = (
        FluentSpecificationBuilder()
        .equals("status", "active")
        .greater_than("amount", 100)
        .build()
    )

    assert len(spec.filters) == 3  # status + amount + deleted_at(auto)
    assert spec.filters[0].field == "status"
    assert spec.filters[0].value == "active"


def test_fluent_builder_pagination():
    """测试分页"""
    spec = FluentSpecificationBuilder().paginate(page=2, size=50).build()

    assert spec.limit == 50
    assert spec.offset == 50  # (page-1) * size = 1 * 50


def test_fluent_builder_soft_delete():
    """测试软删除控制"""
    # 默认过滤
    spec1 = FluentSpecificationBuilder().equals("status", "active").build()
    assert any(f.field == "deleted_at" for f in spec1.filters)

    # 包含已删除
    spec2 = (
        FluentSpecificationBuilder()
        .equals("status", "active")
        .include_deleted()
        .build()
    )
    assert not any(f.field == "deleted_at" for f in spec2.filters)
```

## 常见问题

### Q1: FluentBuilder 和传统 SpecificationBuilder 有什么区别？

**A:**
- `SpecificationBuilder`: 需要手动创建 `Criterion` 对象，代码冗长
- `FluentSpecificationBuilder`: 提供流式 API，代码简洁，可读性高
- 两者生成的 `CompositeSpecification` 完全兼容

### Q2: 为什么默认过滤 `deleted_at IS NULL`？

**A:**
- Bento 的软删除设计理念：默认业务查询不应包含已删除数据
- 如需查询已删除数据，显式调用 `.include_deleted()` 或 `.only_deleted()`

### Q3: `paginate()` 和 `limit/offset` 如何选择？

**A:**
- **推荐 `paginate(page, size)`**: 语义清晰，符合 Bento 风格
- **`limit/offset` 适用于**: 特殊场景（如 "跳过前 100 条，取 10 条"）

### Q4: 如何处理复杂的 OR 逻辑？

**A:**
```python
# 方式 1: 使用 IN（推荐，适用于单字段多值）
spec = (
    FluentSpecificationBuilder(OrderModel)
    .in_("status", ["paid", "shipped"])
    .build()
)

# 方式 2: 组合多个 Specification（适用于复杂跨字段 OR）
spec1 = FluentSpecificationBuilder(OrderModel).equals("status", "paid").build()
spec2 = FluentSpecificationBuilder(OrderModel).equals("priority", "high").build()
combined = spec1.or_(spec2)  # WHERE (status = 'paid') OR (priority = 'high')
```

### Q5: 支持子查询吗？

**A:**
当前版本不支持子查询。如有需求，请使用原生 SQL 或扩展 `FluentSpecificationBuilder`。

## 总结

`FluentSpecificationBuilder` 是 Bento 融合 Legend 优势的成果之一，它显著提升了查询构建的开发体验：

✅ **代码量减少 60%+**
✅ **可读性提升**（接近自然语言）
✅ **类型安全**（IDE 支持 + 静态检查）
✅ **智能默认**（自动处理软删除）
✅ **灵活扩展**（链式调用 + 动态构建）

---

**下一步阅读:**
- [Specification Pattern 核心概念](./SPECIFICATION_PATTERN.md)
- [BaseUseCase 使用指南](./BASEUSE_CASE_GUIDE.md)
- [Fusion Upgrade Plan](../migration/FUSION_UPGRADE_PLAN.md)

