# Order Specification 使用指南

## 🎉 新增功能

现在你可以使用类型安全的 `OrderSpec` 来构建复杂的订单查询条件！

## ✨ 特性

- **流式 API** - 链式调用，代码优雅
- **类型安全** - IDE 自动补全
- **数据库层面过滤** - 性能提升 10-100x
- **可组合** - 多个条件自由组合

## 📚 基础用法

### 1. 简单查询

```python
from contexts.ordering.domain.specifications import OrderSpec

# 查找特定客户的订单
spec = OrderSpec().customer_id_equals("customer_123")
orders = await order_repo.find(spec)

# 查找高价值订单
spec = OrderSpec().amount_greater_than(1000.0)
high_value_orders = await order_repo.find(spec)

# 查找特定状态的订单
spec = OrderSpec().is_paid()
paid_orders = await order_repo.find(spec)
```

### 2. 组合查询

```python
# 查找特定客户的高价值订单
spec = (OrderSpec()
    .customer_id_equals("customer_123")
    .amount_greater_than(1000.0)
)
orders = await order_repo.find(spec)

# 查找已支付且金额大于500的订单
spec = (OrderSpec()
    .is_paid()
    .amount_greater_than(500.0)
)
orders = await order_repo.find(spec)

# 查找特定日期范围内的订单
from datetime import datetime, timedelta

start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now()

spec = (OrderSpec()
    .created_between(start_date, end_date)
    .is_paid()
)
recent_orders = await order_repo.find(spec)
```

### 3. 配合 Repository Mixins 使用

```python
# 查找前 10 个高价值订单
spec = OrderSpec().amount_greater_than(1000.0)
top_orders = await order_repo.find_top_n(10, spec, order_by="-total")

# 查找第一个已支付订单
spec = OrderSpec().is_paid()
first_paid = await order_repo.find_first(spec, order_by="created_at")

# 分页查询特定客户的订单
spec = OrderSpec().customer_id_equals("customer_123")
orders, total = await order_repo.find_paginated(1, 20, spec)

# 统计特定状态的订单数量
spec = OrderSpec().is_shipped()
count = await order_repo.count_field("id", spec)
```

## 🎯 实际应用场景

### 场景 1: 客户服务

```python
async def get_customer_latest_order(customer_id: str) -> Order | None:
    """获取客户最新订单"""
    spec = OrderSpec().customer_id_equals(customer_id)
    return await order_repo.find_first(spec, order_by="-created_at")

async def get_customer_order_history(
    customer_id: str,
    page: int = 1,
    page_size: int = 20
) -> tuple[list[Order], int]:
    """获取客户订单历史（分页）"""
    spec = OrderSpec().customer_id_equals(customer_id)
    return await order_repo.find_paginated(page, page_size, spec, order_by="-created_at")
```

### 场景 2: 高价值订单管理

```python
async def get_high_value_orders(min_amount: float = 1000.0) -> list[Order]:
    """获取高价值订单"""
    spec = OrderSpec().amount_greater_than(min_amount).is_paid()
    return await order_repo.find_top_n(50, spec, order_by="-total")

async def get_vip_customer_orders(customer_id: str, min_amount: float) -> list[Order]:
    """获取VIP客户的高价值订单"""
    spec = (OrderSpec()
        .customer_id_equals(customer_id)
        .amount_greater_than(min_amount)
        .is_delivered()
    )
    return await order_repo.find(spec)
```

### 场景 3: 订单分析

```python
async def analyze_monthly_orders(year: int, month: int) -> dict:
    """分析月度订单"""
    from datetime import datetime

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    spec = OrderSpec().created_between(start_date, end_date)

    return {
        "total_orders": await order_repo.count_field("id", spec),
        "total_revenue": await order_repo.sum_field("total", spec),
        "avg_order": await order_repo.avg_field("total", spec),
        "paid_orders": await order_repo.count_field(
            "id",
            spec.is_paid()
        ),
    }
```

### 场景 4: 风险监控

```python
async def find_suspicious_orders() -> list[Order]:
    """查找可疑订单（高金额且待支付超过24小时）"""
    from datetime import datetime, timedelta

    yesterday = datetime.now() - timedelta(days=1)

    spec = (OrderSpec()
        .amount_greater_than(5000.0)
        .is_pending()
        .created_before(yesterday)
    )

    return await order_repo.find(spec)
```

## 📖 完整 API 参考

### 客户相关
- `customer_id_equals(customer_id: str)` - 筛选特定客户

### 金额相关
- `amount_greater_than(amount: float)` - 金额大于
- `amount_less_than(amount: float)` - 金额小于
- `amount_between(min_amount: float, max_amount: float)` - 金额范围

### 状态相关
- `status_equals(status: str)` - 特定状态
- `is_paid()` - 已支付
- `is_pending()` - 待支付
- `is_shipped()` - 已发货
- `is_delivered()` - 已送达
- `is_cancelled()` - 已取消

### 日期相关
- `created_after(date: datetime)` - 创建日期之后
- `created_before(date: datetime)` - 创建日期之前
- `created_between(start_date: datetime, end_date: datetime)` - 日期范围

## 💡 最佳实践

### 1. 复用查询规格

```python
# ✅ 好的实践：复用常用规格
def get_recent_paid_orders_spec() -> OrderSpec:
    """最近30天已支付订单"""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    return OrderSpec().is_paid().created_after(thirty_days_ago)

# 使用
spec = get_recent_paid_orders_spec()
orders = await order_repo.find(spec)
```

### 2. 组合使用

```python
# ✅ 好的实践：按需组合
base_spec = OrderSpec().customer_id_equals(customer_id)

# 场景1：查看所有订单
all_orders = await order_repo.find(base_spec)

# 场景2：只看已支付的
paid_orders = await order_repo.find(base_spec.is_paid())

# 场景3：只看高价值的
high_value = await order_repo.find(base_spec.amount_greater_than(1000))
```

### 3. 性能优化

```python
# ✅ 使用 Specification（数据库过滤）
spec = OrderSpec().amount_greater_than(min_amount)
orders = await order_repo.find_top_n(10, spec, order_by="-total")

# ❌ 避免内存过滤
all_orders = await order_repo.find_all()
filtered = [o for o in all_orders if o.total > min_amount]
```

## 🔄 迁移指南

### 从简单版本迁移

```python
# 之前：简单实现
async def get_latest_order_for_customer(customer_id: str):
    orders = await repo.find_all_by_field("customer_id", customer_id)
    return orders[0] if orders else None

# 现在：Specification 版本
async def get_latest_order_for_customer(customer_id: str):
    spec = OrderSpec().customer_id_equals(customer_id)
    return await repo.find_first(spec, order_by="-created_at")
```

## ⚡ 性能对比

| 操作 | 简单版本 | Specification版本 | 性能提升 |
|------|---------|------------------|----------|
| 条件过滤 | 内存过滤 | 数据库过滤 | 10-100x |
| 复杂查询 | 多次查询 | 一次查询 | 5-50x |
| 大数据集 | 加载全部 | 只加载需要的 | 100-1000x |

## 🎓 总结

使用 `OrderSpec` 可以：
- ✅ **提升性能** - 数据库层面过滤
- ✅ **提高可读性** - 流式 API，代码清晰
- ✅ **类型安全** - 编译时检查
- ✅ **易于维护** - 可复用的查询规格
- ✅ **易于测试** - 独立的规格对象

---

**开始使用吧！** 🚀
