# Repository Enhancement Proposal

## 当前状态分析

### 已有方法（BaseRepository & RepositoryAdapter）

#### **基础 CRUD**
- ✅ `get(id)` - 根据 ID 查询单个实体
- ✅ `save(aggregate)` - 保存（创建或更新）
- ✅ `delete(aggregate)` - 删除

#### **查询方法**
- ✅ `list(spec)` - 列表查询
- ✅ `find_one(spec)` - 查询单个
- ✅ `find_all(spec)` - 查询所有（list 别名）
- ✅ `find_page(spec, page_params)` - 分页查询
- ✅ `count(spec)` - 计数
- ✅ `exists(spec)` - 存在性检查

#### **批量操作**
- ✅ `save_all(aggregates)` - 批量保存
- ✅ `delete_all(aggregates)` - 批量删除

---

## 🔴 缺失的常用方法

### **1. ID 批量操作**

```python
# ❌ 当前缺失
async def get_by_ids(self, ids: list[ID]) -> list[AR]:
    """批量根据 ID 获取实体"""

async def delete_by_ids(self, ids: list[ID]) -> int:
    """批量根据 ID 删除实体，返回删除数量"""

async def exists_by_id(self, id: ID) -> bool:
    """检查 ID 是否存在"""
```

**使用场景**:
```python
# 订单查询多个商品
product_ids = [ID("p1"), ID("p2"), ID("p3")]
products = await product_repo.get_by_ids(product_ids)

# 批量删除
deleted_count = await order_repo.delete_by_ids(expired_order_ids)
```

---

### **2. 条件更新/删除**

```python
# ❌ 当前缺失
async def update_by_spec(
    self,
    spec: CompositeSpecification[AR],
    updates: dict
) -> int:
    """根据条件批量更新，返回更新数量"""

async def delete_by_spec(
    self,
    spec: CompositeSpecification[AR]
) -> int:
    """根据条件批量删除，返回删除数量"""
```

**使用场景**:
```python
# 批量更新订单状态
spec = OrderSpec().status_equals("PENDING").older_than(days=30)
count = await order_repo.update_by_spec(spec, {"status": "CANCELLED"})

# 批量删除过期数据
spec = LogSpec().older_than(days=90)
deleted = await log_repo.delete_by_spec(spec)
```

---

### **3. 存在性和唯一性检查**

```python
# ❌ 当前缺失
async def exists_by_field(self, field: str, value: Any) -> bool:
    """检查字段值是否存在"""

async def is_unique(self, field: str, value: Any, exclude_id: ID | None = None) -> bool:
    """检查字段值是否唯一（支持排除特定ID）"""

async def find_by_field(self, field: str, value: Any) -> AR | None:
    """根据字段查询单个实体"""
```

**使用场景**:
```python
# 检查邮箱唯一性
if not await user_repo.is_unique("email", "user@example.com"):
    raise ValidationError("Email already exists")

# 更新时检查唯一性（排除当前用户）
if not await user_repo.is_unique("email", new_email, exclude_id=user.id):
    raise ValidationError("Email already taken")

# 根据字段查询
user = await user_repo.find_by_field("email", "admin@example.com")
```

---

### **4. 排序和限制**

```python
# ❌ 当前缺失
async def find_first(
    self,
    spec: CompositeSpecification[AR] | None = None,
    order_by: str | None = None
) -> AR | None:
    """查询第一个实体"""

async def find_last(
    self,
    spec: CompositeSpecification[AR] | None = None,
    order_by: str | None = None
) -> AR | None:
    """查询最后一个实体"""

async def find_top_n(
    self,
    n: int,
    spec: CompositeSpecification[AR] | None = None,
    order_by: str | None = None
) -> list[AR]:
    """查询前 N 个实体"""
```

**使用场景**:
```python
# 查询最新订单
latest_order = await order_repo.find_last(order_by="created_at")

# 查询前 10 个热门商品
top_products = await product_repo.find_top_n(
    10,
    spec=ProductSpec().is_active(),
    order_by="-sales_count"
)
```

---

### **5. 聚合查询**

```python
# ❌ 当前缺失
async def sum_field(
    self,
    field: str,
    spec: CompositeSpecification[AR] | None = None
) -> float:
    """求和"""

async def avg_field(
    self,
    field: str,
    spec: CompositeSpecification[AR] | None = None
) -> float:
    """平均值"""

async def min_field(self, field: str, spec: ...) -> Any:
    """最小值"""

async def max_field(self, field: str, spec: ...) -> Any:
    """最大值"""
```

**使用场景**:
```python
# 计算总营收
total_revenue = await order_repo.sum_field(
    "total",
    spec=OrderSpec().status_in(["PAID", "COMPLETED"])
)

# 平均订单金额
avg_order = await order_repo.avg_field("total")
```

---

### **6. 分组查询**

```python
# ❌ 当前缺失
async def group_by_field(
    self,
    field: str,
    spec: CompositeSpecification[AR] | None = None
) -> dict[Any, int]:
    """按字段分组计数"""

async def group_by_date(
    self,
    date_field: str,
    granularity: str = "day",  # day, week, month, year
    spec: CompositeSpecification[AR] | None = None
) -> dict[str, int]:
    """按日期分组统计"""
```

**使用场景**:
```python
# 按状态统计订单数量
status_counts = await order_repo.group_by_field("status")
# 结果: {"PENDING": 10, "PAID": 25, "SHIPPED": 15}

# 按日期统计订单量
daily_orders = await order_repo.group_by_date("created_at", granularity="day")
# 结果: {"2025-01-01": 5, "2025-01-02": 8, ...}
```

---

### **7. 软删除增强**

```python
# ❌ 当前缺失
async def find_trashed(
    self,
    spec: CompositeSpecification[AR] | None = None
) -> list[AR]:
    """查询已软删除的实体"""

async def restore(self, id: ID) -> AR | None:
    """恢复软删除的实体"""

async def restore_by_spec(self, spec: CompositeSpecification[AR]) -> int:
    """批量恢复"""

async def force_delete(self, aggregate: AR) -> None:
    """硬删除（永久删除）"""
```

**使用场景**:
```python
# 查看回收站
trashed_orders = await order_repo.find_trashed()

# 恢复订单
await order_repo.restore(order_id)

# 永久删除
await order_repo.force_delete(old_order)
```

---

### **8. 事务和锁**

```python
# ❌ 当前缺失
async def get_for_update(self, id: ID) -> AR | None:
    """获取并加悲观锁"""

async def refresh(self, aggregate: AR) -> AR:
    """刷新实体状态（从数据库重新加载）"""

async def detach(self, aggregate: AR) -> None:
    """从 Session 中分离实体"""
```

**使用场景**:
```python
# 悲观锁避免并发冲突
order = await order_repo.get_for_update(order_id)
order.update_status("PAID")
await order_repo.save(order)

# 刷新实体
refreshed_order = await order_repo.refresh(order)
```

---

### **9. 关联查询（对于复杂聚合）**

```python
# ❌ 当前缺失
async def get_with_relations(
    self,
    id: ID,
    relations: list[str]
) -> AR | None:
    """获取实体及其关联实体"""

async def list_with_relations(
    self,
    spec: CompositeSpecification[AR] | None = None,
    relations: list[str] | None = None
) -> list[AR]:
    """列表查询并加载关联"""
```

**使用场景**:
```python
# 加载订单及其商品
order = await order_repo.get_with_relations(
    order_id,
    relations=["items", "customer"]
)

# 列表查询并预加载
orders = await order_repo.list_with_relations(
    spec=OrderSpec().status_equals("PENDING"),
    relations=["items"]
)
```

---

### **10. 随机和采样**

```python
# ❌ 当前缺失
async def find_random(
    self,
    spec: CompositeSpecification[AR] | None = None
) -> AR | None:
    """随机获取一个实体"""

async def find_random_n(
    self,
    n: int,
    spec: CompositeSpecification[AR] | None = None
) -> list[AR]:
    """随机获取 N 个实体"""
```

**使用场景**:
```python
# 随机推荐商品
random_products = await product_repo.find_random_n(
    5,
    spec=ProductSpec().is_active()
)
```

---

## 📊 优先级建议

| 优先级 | 方法 | 使用频率 | 实现难度 |
|-------|------|----------|---------|
| **P0** | get_by_ids, delete_by_ids | 🔥🔥🔥🔥🔥 | 🟢 低 |
| **P0** | exists_by_id, is_unique | 🔥🔥🔥🔥🔥 | 🟢 低 |
| **P0** | find_by_field | 🔥🔥🔥🔥 | 🟢 低 |
| **P1** | update_by_spec, delete_by_spec | 🔥🔥🔥🔥 | 🟡 中 |
| **P1** | find_first, find_last, find_top_n | 🔥🔥🔥 | 🟢 低 |
| **P1** | sum_field, avg_field | 🔥🔥🔥 | 🟡 中 |
| **P2** | group_by_field, group_by_date | 🔥🔥 | 🟡 中 |
| **P2** | find_trashed, restore | 🔥🔥 | 🟡 中 |
| **P2** | get_for_update, refresh | 🔥🔥 | 🟡 中 |
| **P3** | get_with_relations | 🔥 | 🔴 高 |
| **P3** | find_random_n | 🔥 | 🟡 中 |

---

## 🎯 实施建议

### 阶段 1: 基础增强（P0）

实现最常用的方法：
- ✅ 批量 ID 操作
- ✅ 唯一性检查
- ✅ 字段查询

**预期收益**: 减少 60% 的自定义查询代码

### 阶段 2: 高级查询（P1）

实现高级查询功能：
- ✅ 条件更新/删除
- ✅ 排序和限制
- ✅ 聚合查询

**预期收益**: 减少 40% 的复杂查询代码

### 阶段 3: 特殊场景（P2-P3）

根据实际需求实现：
- ✅ 分组查询
- ✅ 软删除增强
- ✅ 事务和锁

---

## 📝 实现示例

### 示例 1: get_by_ids

```python
# RepositoryAdapter
async def get_by_ids(self, ids: list[ID]) -> list[AR]:
    """批量根据 ID 获取实体"""
    pos = await self._repository.get_po_by_ids(ids)
    return self._mapper.map_reverse_list(pos)

# BaseRepository
async def get_po_by_ids(self, ids: list[ID]) -> list[PO]:
    """批量获取 PO"""
    result = await self.session.execute(
        select(self._po_type).where(
            self._po_type.id.in_([str(id) for id in ids])
        )
    )
    return list(result.scalars().all())
```

### 示例 2: is_unique

```python
# RepositoryAdapter
async def is_unique(
    self,
    field: str,
    value: Any,
    exclude_id: ID | None = None
) -> bool:
    """检查字段值唯一性"""
    return await self._repository.is_field_unique(field, value, exclude_id)

# BaseRepository
async def is_field_unique(
    self,
    field: str,
    value: Any,
    exclude_id: ID | None = None
) -> bool:
    """检查字段唯一性"""
    query = select(self._po_type).where(
        getattr(self._po_type, field) == value
    )
    if exclude_id:
        query = query.where(self._po_type.id != str(exclude_id))

    result = await self.session.execute(query)
    return result.scalar_one_or_none() is None
```

---

## ✅ 总结

当前 Repository 实现**基础功能完整，但缺少常用的便捷方法**。

建议按优先级逐步添加：
1. **P0** - 立即实施（1周）
2. **P1** - 近期实施（2周）
3. **P2-P3** - 按需实施

**预期总体收益**:
- 减少 50%+ 的自定义查询代码
- 提升 40% 的开发效率
- 统一 API 风格，提高可维护性
