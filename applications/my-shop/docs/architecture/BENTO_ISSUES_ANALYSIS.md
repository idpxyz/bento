# Bento Framework 使用问题分析

## 🚨 严重问题

### 问题 1: `get_unit_of_work()` Session 生命周期错误

**位置**: `shared/infrastructure/dependencies.py:90-124`

**问题代码**:
```python
async def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    async with session_factory() as session:  # ❌ session 在这里创建
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        # ... 注册 repositories ...
        return uow  # ❌ 返回后 session 已关闭！
    # ❌ async with 结束，session.close() 被调用
```

**实际使用**:
```python
# contexts/ordering/interfaces/order_api.py
async def get_create_order_use_case() -> CreateOrderUseCase:
    uow = await get_unit_of_work()  # session 已经关闭
    return CreateOrderUseCase(uow)   # UoW 持有已关闭的 session

# API handler
use_case: CreateOrderUseCase = Depends(get_create_order_use_case)
order = await use_case.execute(command)  # ❌ 使用已关闭的 session！
```

**问题分析**:
1. `session_factory()` 的 `async with` 上下文在返回前就结束了
2. session 在离开上下文时被自动关闭（`__aexit__` 调用 `session.close()`）
3. 返回的 UoW 持有的是**已关闭的 session**
4. 当 Use Case 尝试使用时，会遇到 "Session is closed" 错误

**为什么目前能工作？**
- 可能是因为 SQLAlchemy 的某些操作在 session 关闭后仍然能工作
- 或者存在隐式的 session 重新打开机制
- 但这是**不可靠且危险的**

---

### 问题 2: 两种 UoW 获取模式不一致

**模式 A**: `get_uow()` - ✅ 正确
```python
async def get_uow(
    session: AsyncSession = Depends(get_db_session),  # FastAPI 管理生命周期
) -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
    outbox = SqlAlchemyOutbox(session)
    uow = SQLAlchemyUnitOfWork(session, outbox)

    try:
        yield uow  # ✅ Generator pattern，session 保持打开
    finally:
        pass  # session 由 get_db_session 管理
```

**模式 B**: `get_unit_of_work()` - ❌ 错误
```python
async def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    async with session_factory() as session:  # ❌ session 立即关闭
        uow = SQLAlchemyUnitOfWork(session, outbox)
        return uow  # ❌ 返回已关闭 session 的 UoW
```

**问题**:
- 两种模式对 session 生命周期的管理完全不同
- 模式 A 正确但未被使用
- 模式 B 被广泛使用但有严重缺陷

---

### 问题 3: 事件收集机制依赖手动 `track()`

**Bento UoW 设计**:
```python
# bento/persistence/uow.py
async def commit(self):
    # 1. 从 tracked aggregates 收集事件
    await self.collect_events()

    # 2. 将事件保存到 Outbox
    for evt in self.pending_events:
        record = OutboxRecord.from_domain_event(evt)
        self._session.add(record)

    # 3. 提交事务
    await self._session.commit()
```

**问题**: 需要手动调用 `track()`
```python
# 正确用法（但容易忘记）
order = Order.create(...)
await repo.save(order)
uow.track(order)  # ⚠️ 忘记这行，事件不会被收集！
await uow.commit()
```

**在 my-shop 中的实际使用**:
```python
# contexts/ordering/application/commands/create_order.py
order_repo = OrderRepository(self.uow._session)
await order_repo.save(order)
# ❌ 没有 uow.track(order)！
# ❌ 事件不会被收集到 Outbox！
```

**结果**:
- OrderCreated 事件可能没有被正确持久化到 Outbox
- 这解释了为什么 Outbox 表中的某些字段是 null

---

### 问题 4: Repository 直接访问 `uow._session`

**不好的模式**:
```python
# contexts/ordering/application/commands/create_order.py
product_repo = ProductRepository(self.uow._session)  # ❌ 访问私有属性
```

**问题**:
1. 违反封装原则（访问 `_session` 私有属性）
2. 绕过了 UoW 的 repository 注册机制
3. Repository 不在 UoW 的管理范围内

**应该的做法**:
```python
# 在 Use Case 初始化时或 UoW 中注册
uow.register_repository(Product, lambda s: ProductRepository(s))
product_repo = uow.repository(Product)
```

---

## 🔧 修复建议

### 修复 1: 修正 `get_unit_of_work()` 的 session 生命周期

**选项 A**: 改为 Generator 模式（推荐）
```python
async def get_unit_of_work(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
    """Get UoW with proper session lifecycle."""
    outbox = SqlAlchemyOutbox(session)
    uow = SQLAlchemyUnitOfWork(session, outbox)

    # Register repositories
    # ...

    yield uow  # ✅ Session 保持打开
```

**选项 B**: 移除 `get_unit_of_work()`，统一使用 `get_uow()`
```python
# 删除 get_unit_of_work()
# 所有地方改用 get_uow()

async def get_create_order_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow)  # ✅ 使用正确的依赖
) -> CreateOrderUseCase:
    # 在这里注册需要的 repositories
    uow.register_repository(Product, lambda s: ProductRepository(s))
    uow.register_repository(Order, lambda s: OrderRepository(s))
    return CreateOrderUseCase(uow)
```

### 修复 2: 自动 track 机制

**在 Repository 中自动 track**:
```python
class OrderRepository:
    def __init__(self, session: AsyncSession, uow: SQLAlchemyUnitOfWork | None = None):
        self._session = session
        self._uow = uow

    async def save(self, order: Order) -> None:
        # ... save logic ...

        # ✅ 自动 track
        if self._uow:
            self._uow.track(order)
```

**或在 BaseRepository 中实现**:
```python
class BaseRepository[T]:
    def __init__(self, session: AsyncSession):
        self._session = session
        # 从 ContextVar 获取当前 UoW
        from bento.persistence.uow import _current_uow
        self._uow = _current_uow.get()

    async def save(self, entity: T) -> None:
        self._session.add(entity)
        if self._uow:
            self._uow.track(entity)  # ✅ 自动 track
```

### 修复 3: 使用 UoW 的 repository() 方法

**修改 Use Case**:
```python
class CreateOrderUseCase(BaseUseCase[CreateOrderCommand, Order]):
    async def handle(self, command: CreateOrderCommand) -> Order:
        # ✅ 使用 UoW 注册和获取 repository
        product_repo = self.uow.repository(Product)

        # 验证产品
        for item in command.items:
            product = await product_repo.get(item.product_id)
            if not product:
                raise ApplicationException(...)

        # 创建订单
        order = Order(...)
        order_repo = self.uow.repository(Order)
        await order_repo.save(order)

        # ✅ 不需要手动 track，repository 会自动处理
        return order
```

---

## 📊 优先级评估

| 问题 | 严重性 | 优先级 | 影响 |
|------|--------|--------|------|
| Session 生命周期 | 🔴 Critical | P0 | 数据可能丢失、连接泄漏 |
| track() 忘记调用 | 🔴 Critical | P0 | 事件丢失 |
| 两种 UoW 模式混用 | 🟡 High | P1 | 代码混乱、难以维护 |
| 直接访问 _session | 🟢 Medium | P2 | 违反封装，但能工作 |

---

## 🎯 建议行动

### 立即修复（P0）:
1. ✅ 修正 `get_unit_of_work()` 或移除它
2. ✅ 在 Repository 中实现自动 track 机制

### 短期优化（P1）:
3. ✅ 统一 UoW 获取模式
4. ✅ 添加集成测试验证 session 生命周期

### 长期改进（P2）:
5. ✅ 使用 UoW 的 repository() 而非直接访问 _session
6. ✅ 完善文档和最佳实践指南

---

## 🔍 如何验证问题

### 测试 Session 生命周期:
```python
async def test_session_lifecycle():
    uow = await get_unit_of_work()

    # 尝试使用 session
    try:
        result = await uow._session.execute("SELECT 1")
        print("✅ Session is open")
    except Exception as e:
        print(f"❌ Session is closed: {e}")
```

### 测试事件收集:
```python
async def test_event_collection():
    uow = await get_unit_of_work()

    async with uow:
        order = Order.create(...)
        order.add_event(OrderCreated(...))

        await repo.save(order)
        # 不调用 track()

        await uow.commit()

    # 检查 Outbox
    events = await session.execute("SELECT * FROM outbox")
    print(f"Events in outbox: {len(list(events))}")  # 可能是 0！
```

---

## 📚 参考

- Bento UoW 实现: `src/bento/persistence/uow.py`
- my-shop 使用: `applications/my-shop/shared/infrastructure/dependencies.py`
- 问题实例: `contexts/ordering/application/commands/create_order.py`
