# Repository Mixins 快速参考

## 🚀 29个增强方法速查表

### P0: 基础增强 (6个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `get_by_ids(ids)` | 批量获取 | `await repo.get_by_ids([id1, id2])` |
| `exists_by_id(id)` | ID存在性检查 | `if await repo.exists_by_id(id):` |
| `delete_by_ids(ids)` | 批量删除 | `count = await repo.delete_by_ids(ids)` |
| `is_unique(field, value)` | 唯一性验证 | `await repo.is_unique("email", email)` |
| `find_by_field(field, value)` | 字段查找 | `user = await repo.find_by_field("email", email)` |
| `find_all_by_field(field, value)` | 批量字段查找 | `orders = await repo.find_all_by_field("customer_id", id)` |

### P1: 高级查询 (13个)

#### 聚合查询 (5个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `sum_field(field)` | 求和 | `total = await repo.sum_field("price")` |
| `avg_field(field)` | 平均值 | `avg = await repo.avg_field("price")` |
| `min_field(field)` | 最小值 | `min = await repo.min_field("price")` |
| `max_field(field)` | 最大值 | `max = await repo.max_field("price")` |
| `count_field(field)` | 计数 | `count = await repo.count_field("id")` |

#### 排序限制 (4个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `find_first(order_by)` | 第一个 | `first = await repo.find_first(order_by="-created_at")` |
| `find_last(order_by)` | 最后一个 | `last = await repo.find_last(order_by="created_at")` |
| `find_top_n(n, order_by)` | 前N个 | `top10 = await repo.find_top_n(10, order_by="-rating")` |
| `find_paginated(page, size)` | 分页 | `items, total = await repo.find_paginated(1, 20)` |

#### 条件更新 (4个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `update_by_spec(spec, updates)` | 批量更新 | `count = await repo.update_by_spec(spec, {"status": "DONE"})` |
| `delete_by_spec(spec)` | 条件删除 | `count = await repo.delete_by_spec(spec)` |
| `soft_delete_by_spec(spec)` | 条件软删除 | `count = await repo.soft_delete_by_spec(spec)` |
| `restore_by_spec(spec)` | 批量恢复 | `count = await repo.restore_by_spec(spec)` |

### P2: 分析增强 (7个)

#### 分组查询 (3个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `group_by_field(field)` | 按字段分组 | `stats = await repo.group_by_field("status")` |
| `group_by_date(field, granularity)` | 按日期分组 | `daily = await repo.group_by_date("created_at", "day")` |
| `group_by_multiple_fields(fields)` | 多字段分组 | `stats = await repo.group_by_multiple_fields(["status", "type"])` |

#### 软删除增强 (4个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `find_trashed()` | 查找已删除 | `trashed = await repo.find_trashed()` |
| `find_with_trashed()` | 包含已删除 | `all = await repo.find_with_trashed()` |
| `count_trashed()` | 统计已删除 | `count = await repo.count_trashed()` |
| `is_trashed(id)` | 检查是否删除 | `if await repo.is_trashed(id):` |

### P3: 特殊功能 (3个)

| 方法 | 用途 | 示例 |
|------|------|------|
| `find_random()` | 随机1个 | `item = await repo.find_random()` |
| `find_random_n(n)` | 随机N个 | `items = await repo.find_random_n(5)` |
| `sample_percentage(pct)` | 百分比采样 | `sample = await repo.sample_percentage(10.0)` |

## 💡 常用场景速查

### 数据验证

```python
# 邮箱唯一性
if not await user_repo.is_unique("email", email):
    raise EmailExistsError()

# 更新时排除自身
if not await user_repo.is_unique("email", new_email, exclude_id=user.id):
    raise EmailExistsError()

# 检查ID存在
if not await order_repo.exists_by_id(order_id):
    raise OrderNotFoundError()
```

### 批量操作

```python
# 批量获取
users = await user_repo.get_by_ids([id1, id2, id3])

# 批量删除
deleted = await data_repo.delete_by_ids(expired_ids)

# 条件批量更新
spec = OrderSpec().status_equals("PENDING").older_than(days=30)
await order_repo.update_by_spec(spec, {"status": "CANCELLED"})
```

### 统计分析

```python
# 基本统计
total_revenue = await order_repo.sum_field("total")
avg_price = await product_repo.avg_field("price")
max_score = await exam_repo.max_field("score")

# 分组统计
status_dist = await order_repo.group_by_field("status")
daily_orders = await order_repo.group_by_date("created_at", "day")
category_stats = await product_repo.group_by_multiple_fields(["category", "brand"])
```

### 排序查询

```python
# 最新/最早
latest = await post_repo.find_first(order_by="-created_at")
oldest = await post_repo.find_last(order_by="created_at")

# Top N
top_rated = await product_repo.find_top_n(10, order_by="-rating")
cheapest_5 = await product_repo.find_top_n(5, order_by="price")

# 分页
products, total = await product_repo.find_paginated(
    page=1,
    page_size=20,
    order_by="name"
)
```

### 随机推荐

```python
# 单个推荐
featured = await product_repo.find_random()

# 多个推荐
recommendations = await product_repo.find_random_n(10)

# 按条件推荐
active_spec = ProductSpec().is_active()
featured = await product_repo.find_random_n(5, active_spec)

# 百分比采样
audit_sample = await order_repo.sample_percentage(10.0, max_count=1000)
```

### 软删除管理

```python
# 查看回收站
trashed_users = await user_repo.find_trashed()
trashed_count = await user_repo.count_trashed()

# 检查是否删除
if await user_repo.is_trashed(user_id):
    print("用户已删除")

# 批量软删除
spec = UserSpec().inactive_for_days(180)
await user_repo.soft_delete_by_spec(spec)

# 批量恢复
spec = UserSpec().deleted_within_days(7)
await user_repo.restore_by_spec(spec)
```

## ⚠️ 注意事项

### 性能优化

✅ **使用批量操作**
```python
# 好
users = await repo.get_by_ids(ids)

# 避免
users = [await repo.get_by_id(id) for id in ids]
```

✅ **使用聚合查询**
```python
# 好
total = await repo.sum_field("amount")

# 避免
orders = await repo.find_all()
total = sum(o.amount for o in orders)
```

✅ **使用分页**
```python
# 好
items, total = await repo.find_paginated(page, size)

# 避免
all_items = await repo.find_all()
```

### 事务和事件

⚠️ **批量操作不触发事件**

`update_by_spec`、`delete_by_spec` 等批量操作绕过拦截器，不会触发领域事件。

```python
# 不触发事件（性能优先）
await repo.update_by_spec(spec, updates)

# 触发事件（需要时）
for order in orders:
    order.cancel()
    await repo.save(order)
```

### Specification 使用

建议结合 Specification 模式：

```python
# 定义可复用规格
class OrderSpec(CompositeSpecification):
    def is_pending(self):
        return self.and_spec(FieldEquals("status", "PENDING"))

    def older_than(self, days: int):
        cutoff = datetime.now() - timedelta(days=days)
        return self.and_spec(FieldLessThan("created_at", cutoff))

# 组合使用
spec = OrderSpec().is_pending().older_than(30)
count = await repo.update_by_spec(spec, {"status": "CANCELLED"})
```

## 🔗 相关文档

- [完整使用指南](./REPOSITORY_MIXINS_GUIDE.md) - 详细说明和最佳实践
- [Specification 使用指南](./SPECIFICATION_USAGE.md) - 规范模式详解
- [Repository Enhancement Proposal](./REPOSITORY_ENHANCEMENT_PROPOSAL.md) - 设计提案

## 📊 方法分类速览

```
Repository Mixins (29个方法)
│
├── P0: 基础增强 (6个)
│   ├── 批量ID操作 (3个): get_by_ids, exists_by_id, delete_by_ids
│   └── 唯一性检查 (3个): is_unique, find_by_field, find_all_by_field
│
├── P1: 高级查询 (13个)
│   ├── 聚合查询 (5个): sum/avg/min/max/count_field
│   ├── 排序限制 (4个): find_first/last/top_n, find_paginated
│   └── 条件更新 (4个): update/delete/soft_delete/restore_by_spec
│
├── P2: 分析增强 (7个)
│   ├── 分组查询 (3个): group_by_field/date/multiple_fields
│   └── 软删除增强 (4个): find_trashed/with_trashed, count_trashed, is_trashed
│
└── P3: 特殊功能 (3个)
    └── 随机采样 (3个): find_random, find_random_n, sample_percentage
```

---

**提示**：所有方法都支持可选的 `spec` 参数用于过滤条件！
