## CQRS 读模型实现指南

### 📐 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                    Command Side (写侧)                        │
├──────────────────────────────────────────────────────────────┤
│  Command → Handler → Domain Model → Repository               │
│  创建订单   处理逻辑   Order实体      OrderRepository         │
│                            ↓                                  │
│                       OrderModel (写模型)                     │
│                            ↓                                  │
│                      领域事件发布                             │
│                    (OrderCreated事件)                        │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          │ Event Bus
                          ↓
┌──────────────────────────────────────────────────────────────┐
│                    Query Side (读侧)                          │
├──────────────────────────────────────────────────────────────┤
│  Event → Projection → OrderReadModel (读模型)                │
│  订单创建   投影处理    - total_amount (预计算)               │
│                         - items_count (预计算)                │
│                         - 优化索引                            │
│                            ↓                                  │
│              Query → OrderReadService                         │
│              查询     ✅ 数据库级过滤                          │
│                      ✅ 无需JOIN                              │
│                      ✅ 高性能查询                            │
└──────────────────────────────────────────────────────────────┘
```

### 🎯 核心组件

#### 1. 读模型 (Read Model)

**位置**: `persistence/models/order_read_model.py`

```python
class OrderReadModel(Base):
    """CQRS 读模型 - 查询优化"""
    __tablename__ = "order_read_models"

    id: Mapped[str]
    customer_id: Mapped[str]
    status: Mapped[str]

    # ⭐ 预计算字段 - 关键优势
    total_amount: Mapped[float]  # 从items计算，存储以便数据库过滤
    items_count: Mapped[int]      # 订单商品数量

    # 时间戳
    created_at: Mapped[datetime]
    paid_at: Mapped[datetime | None]
```

**优势**:
- ✅ `total_amount` 存储在数据库 → 可以 WHERE/ORDER BY
- ✅ 无需 JOIN items 表 → 查询更快
- ✅ 专门的索引 → 优化常见查询

#### 2. 投影 (Projection)

**位置**: `application/projections/order_projection.py`

```python
class OrderProjection:
    """将写模型投影到读模型"""

    async def handle_order_created(self, event: OrderCreated):
        """订单创建事件 → 创建读模型"""
        # 1. 从写模型获取数据
        order_po = await fetch_order(event.order_id)

        # 2. 计算衍生字段
        total_amount = sum(item.quantity * item.unit_price
                          for item in order_po.items)

        # 3. 创建读模型
        read_model = OrderReadModel(
            id=order_po.id,
            total_amount=total_amount,  # 预计算
            items_count=len(order_po.items),
            ...
        )
        await session.add(read_model)
```

**职责**:
- 监听领域事件
- 更新读模型
- 保持数据同步

#### 3. 读服务 (Read Service)

**位置**: `application/queries/order_read_service.py`

```python
class OrderReadService:
    """使用读模型的查询服务"""

    async def search_orders(
        self,
        min_amount: float | None = None,
        max_amount: float | None = None
    ):
        stmt = select(OrderReadModel)

        # ✅ 数据库级过滤 - 高性能！
        if min_amount:
            stmt = stmt.where(OrderReadModel.total_amount >= min_amount)
        if max_amount:
            stmt = stmt.where(OrderReadModel.total_amount <= max_amount)

        # ✅ 可以使用索引排序
        stmt = stmt.order_by(OrderReadModel.total_amount.desc())

        return await session.execute(stmt)
```

### 🔄 数据同步流程

#### 方式 1: 事件驱动（推荐）

```python
# 1. 命令处理器发布事件
class CreateOrderHandler:
    async def handle(self, cmd: CreateOrderCommand):
        order = Order.create(...)
        await repo.save(order)

        # ✅ 事件自动发布（通过 AggregateRoot）
        # OrderCreated 事件被添加到 order._events

# 2. 事件处理器调用投影
class OrderEventHandler:
    async def on_order_created(self, event: OrderCreated):
        # 更新读模型
        await projection.handle_order_created(event)
```

#### 方式 2: 数据库触发器

```sql
-- PostgreSQL 触发器示例
CREATE OR REPLACE FUNCTION sync_order_read_model()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO order_read_models (
        id, customer_id, status, total_amount, items_count, created_at
    )
    SELECT
        NEW.id,
        NEW.customer_id,
        NEW.status,
        (SELECT SUM(quantity * unit_price) FROM order_items WHERE order_id = NEW.id),
        (SELECT COUNT(*) FROM order_items WHERE order_id = NEW.id),
        NEW.created_at
    ON CONFLICT (id) DO UPDATE SET
        status = EXCLUDED.status,
        total_amount = EXCLUDED.total_amount,
        items_count = EXCLUDED.items_count;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_read_model_sync
AFTER INSERT OR UPDATE ON orders
FOR EACH ROW EXECUTE FUNCTION sync_order_read_model();
```

### 📊 性能对比

#### 查询: 按金额范围查找订单

**写模型查询（旧方式）**:
```python
# ❌ 需要 JOIN + 应用层过滤
orders = await session.execute(
    select(OrderModel).options(selectinload(OrderModel.items))
)
# 在内存中过滤
filtered = [o for o in orders if 100 <= o.total_amount <= 500]
```

**性能**:
- 查询时间: ~200ms (需要加载所有订单和items)
- 内存使用: 高（加载所有数据）
- 无法使用数据库索引

**读模型查询（新方式）**:
```python
# ✅ 数据库级过滤
orders = await session.execute(
    select(OrderReadModel)
    .where(OrderReadModel.total_amount.between(100, 500))
)
```

**性能**:
- 查询时间: ~10ms (使用索引)
- 内存使用: 低（只加载匹配的记录）
- 可以使用 ORDER BY + LIMIT

### 🚀 使用示例

```python
from applications.ecommerce.modules.order.application.queries import OrderReadService
from applications.ecommerce.modules.order.application.projections import OrderProjection

# 1. 创建订单 (写侧)
order = Order.create(order_id=ID.generate(), customer_id=customer_id)
await order_repo.save(order)  # 事件自动发布

# 2. 事件处理 (投影)
projection = OrderProjection(session)
await projection.handle_order_created(OrderCreated(...))

# 3. 查询订单 (读侧)
read_service = OrderReadService(session)
results = await read_service.search_orders(
    min_amount=100.0,
    max_amount=500.0,
    status="pending",
    limit=20
)
# ✅ 高性能：数据库级过滤 + 索引优化
```

### ⚖️ Trade-offs

| 方面 | 写模型查询 | 读模型查询 |
|------|-----------|-----------|
| **一致性** | ✅ 强一致 | ⚠️ 最终一致 |
| **性能** | ❌ 慢（JOIN + 应用层过滤）| ✅ 快（索引 + 数据库过滤）|
| **存储** | ✅ 无额外存储 | ❌ 需要额外表 |
| **维护** | ✅ 简单 | ⚠️ 需要同步逻辑 |
| **查询能力** | ❌ 计算字段难查询 | ✅ 预计算字段可查询 |

### 🎯 何时使用读模型？

**✅ 应该使用**:
- 复杂的聚合查询（统计、报表）
- 需要按计算字段过滤/排序
- 高并发的查询场景
- 跨聚合根的查询

**❌ 不需要使用**:
- 简单的 ID 查询
- 低流量的管理界面
- 实时性要求极高的场景
- 数据量很小的系统

### 🔧 实现清单

- [x] 创建读模型表 (`OrderReadModel`)
- [x] 创建投影器 (`OrderProjection`)
- [x] 创建读服务 (`OrderReadService`)
- [ ] 连接事件总线（事件 → 投影）
- [ ] 创建数据库迁移
- [ ] 实现重建脚本（初始数据同步）
- [ ] 添加监控（读写模型一致性检查）

### 📚 相关文档

- CQRS Pattern: https://martinfowler.com/bliki/CQRS.html
- Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Read Model Projections: https://www.eventstore.com/blog/event-sourcing-and-cqrs

