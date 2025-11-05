# 测试指南

本文档提供 Bento DDD 框架中的全面测试策略，涵盖单元测试、集成测试和端到端测试。

## 📋 目录

- [测试金字塔](#测试金字塔)
- [单元测试](#单元测试)
- [集成测试](#集成测试)
- [端到端测试](#端到端测试)
- [测试工具与技巧](#测试工具与技巧)
- [Fixture 管理](#fixture-管理)
- [Mock 与 Stub](#mock-与-stub)
- [测试数据](#测试数据)
- [性能测试](#性能测试)

---

## 测试金字塔

```
         ▲
        ╱ ╲
       ╱E2E╲           10% - 慢、昂贵、脆弱
      ╱─────╲
     ╱       ╲
    ╱  集成测试 ╲       20% - 中速、适度成本
   ╱───────────╲
  ╱             ╲
 ╱   单元测试     ╲     70% - 快、便宜、稳定
╱─────────────────╲
```

### 测试分布建议

| 类型 | 比例 | 速度 | 特点 | 示例数量 |
|-----|------|-----|------|---------|
| **单元测试** | 70% | < 100ms | 测试单个函数/类 | 700+ |
| **集成测试** | 20% | 100ms-1s | 测试组件协作 | 200+ |
| **E2E测试** | 10% | 1s-10s | 测试完整流程 | 100+ |

### 测试目标

```python
# tests/
├── unit/              # 单元测试 - 快速、隔离
│   ├── domain/        # 领域逻辑测试
│   ├── application/   # 用例测试
│   └── core/          # 核心工具测试
├── integration/       # 集成测试 - 组件协作
│   ├── persistence/   # 数据库集成
│   ├── messaging/     # 事件总线集成
│   └── infrastructure/# 基础设施集成
└── e2e/              # 端到端测试 - 完整流程
    ├── api/          # API测试
    └── scenarios/    # 业务场景测试
```

---

## 单元测试

### 原则

1. **快速**: 每个测试 < 100ms
2. **隔离**: 不依赖外部系统（数据库、网络等）
3. **可重复**: 每次运行结果相同
4. **自解释**: 测试名称清晰表达意图

### Domain 层测试

#### 实体测试

```python
# tests/unit/domain/test_order.py
from decimal import Decimal
import pytest
from bento.domain.order import Order, OrderItem, OrderStatus
from bento.domain.value_objects import Money
from bento.core.result import Ok, Err

class TestOrderCreation:
    """订单创建相关测试"""
    
    def test_create_order_initializes_with_pending_status(self):
        """测试创建订单时状态为 PENDING"""
        # Arrange & Act
        order = Order.create(customer_id="customer-1")
        
        # Assert
        assert order.status == OrderStatus.PENDING
        assert order.customer_id == "customer-1"
        assert len(order.items) == 0
        assert order.total == Money.zero()
    
    def test_create_order_publishes_domain_event(self):
        """测试创建订单时发布领域事件"""
        # Arrange & Act
        order = Order.create(customer_id="customer-1")
        events = order.collect_events()
        
        # Assert
        assert len(events) == 1
        assert events[0].event_type == "order.created.v1"
        assert events[0].customer_id == "customer-1"

class TestOrderBehavior:
    """订单业务逻辑测试"""
    
    def test_add_item_increases_total(self):
        """测试添加订单项会更新总价"""
        # Arrange
        order = Order.create("customer-1")
        
        # Act
        result = order.add_item(
            product_id="product-1",
            quantity=2,
            unit_price=Money(Decimal("100.00"), "USD")
        )
        
        # Assert
        assert result.is_ok
        assert len(order.items) == 1
        assert order.total == Money(Decimal("200.00"), "USD")
    
    def test_add_item_to_confirmed_order_fails(self):
        """测试无法向已确认订单添加商品"""
        # Arrange
        order = Order.create("customer-1")
        order.add_item("product-1", 1, Money(Decimal("100"), "USD"))
        order.confirm()
        
        # Act
        result = order.add_item("product-2", 1, Money(Decimal("50"), "USD"))
        
        # Assert
        assert result.is_err
        assert "Cannot modify" in result.unwrap_err()
    
    def test_confirm_empty_order_fails(self):
        """测试无法确认空订单"""
        # Arrange
        order = Order.create("customer-1")
        
        # Act
        result = order.confirm()
        
        # Assert
        assert result.is_err
        assert "empty order" in result.unwrap_err()
    
    def test_cancel_pending_order_succeeds(self):
        """测试可以取消待处理订单"""
        # Arrange
        order = Order.create("customer-1")
        order.add_item("product-1", 1, Money(Decimal("100"), "USD"))
        
        # Act
        result = order.cancel(reason="Customer request")
        
        # Assert
        assert result.is_ok
        assert order.status == OrderStatus.CANCELLED
```

#### 值对象测试

```python
# tests/unit/domain/test_money.py
from decimal import Decimal
import pytest
from bento.domain.value_objects import Money

class TestMoney:
    """金额值对象测试"""
    
    def test_money_is_immutable(self):
        """测试 Money 不可变"""
        money = Money(Decimal("100.00"), "USD")
        
        with pytest.raises(AttributeError):
            money.amount = Decimal("200.00")
    
    def test_add_same_currency_succeeds(self):
        """测试相同币种金额相加"""
        # Arrange
        money1 = Money(Decimal("100.00"), "USD")
        money2 = Money(Decimal("50.00"), "USD")
        
        # Act
        result = money1.add(money2)
        
        # Assert
        assert result.amount == Decimal("150.00")
        assert result.currency == "USD"
        # 原对象不变
        assert money1.amount == Decimal("100.00")
    
    def test_add_different_currency_fails(self):
        """测试不同币种金额相加失败"""
        # Arrange
        usd = Money(Decimal("100.00"), "USD")
        cny = Money(Decimal("100.00"), "CNY")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Currency mismatch"):
            usd.add(cny)
    
    def test_negative_amount_raises_error(self):
        """测试负金额抛出异常"""
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            Money(Decimal("-10.00"), "USD")
    
    @pytest.mark.parametrize("amount,expected", [
        (Decimal("0"), True),
        (Decimal("0.00"), True),
        (Decimal("0.01"), False),
    ])
    def test_is_zero(self, amount, expected):
        """测试零值判断"""
        money = Money(amount, "USD")
        assert money.is_zero() == expected
```

#### Specification 测试

```python
# tests/unit/domain/test_specifications.py
from bento.domain.order import Order
from bento.domain.specifications import HighValueOrderSpec, VIPCustomerSpec

class TestOrderSpecifications:
    """订单规格测试"""
    
    def test_high_value_order_specification(self):
        """测试高价值订单规格"""
        # Arrange
        spec = HighValueOrderSpec(threshold=Money(Decimal("1000"), "USD"))
        
        high_value_order = self._create_order_with_total(Decimal("1500"))
        low_value_order = self._create_order_with_total(Decimal("500"))
        
        # Act & Assert
        assert spec.is_satisfied_by(high_value_order) is True
        assert spec.is_satisfied_by(low_value_order) is False
    
    def test_and_specification(self):
        """测试组合规格（AND）"""
        # Arrange
        high_value_spec = HighValueOrderSpec(Money(Decimal("1000"), "USD"))
        vip_spec = VIPCustomerSpec()
        combined_spec = high_value_spec.and_(vip_spec)
        
        order = self._create_order_with_total(Decimal("1500"))
        order.customer.vip_status = True
        
        # Act & Assert
        assert combined_spec.is_satisfied_by(order) is True
```

### Application 层测试

#### UseCase 测试

```python
# tests/unit/application/test_create_order.py
import pytest
from bento.application.create_order import CreateOrder, CreateOrderInput
from bento.domain.order import Order
from tests.doubles import InMemoryOrderRepository, InMemoryUnitOfWork

class TestCreateOrderUseCase:
    """创建订单用例测试"""
    
    @pytest.fixture
    def use_case(self):
        """创建用例实例"""
        repo = InMemoryOrderRepository()
        uow = InMemoryUnitOfWork()
        return CreateOrder(order_repo=repo, uow=uow)
    
    async def test_create_order_with_valid_input_succeeds(self, use_case):
        """测试有效输入创建订单成功"""
        # Arrange
        input_dto = CreateOrderInput(
            customer_id="customer-1",
            items=[
                {"product_id": "p1", "quantity": 2, "unit_price": 100.00},
                {"product_id": "p2", "quantity": 1, "unit_price": 50.00},
            ]
        )
        
        # Act
        result = await use_case(input_dto)
        
        # Assert
        assert result.is_ok
        output = result.unwrap()
        assert output.order_id is not None
        assert output.total_amount == Decimal("250.00")
    
    async def test_create_order_saves_to_repository(self, use_case):
        """测试订单被保存到仓储"""
        # Arrange
        input_dto = CreateOrderInput(
            customer_id="customer-1",
            items=[{"product_id": "p1", "quantity": 1, "unit_price": 100}]
        )
        
        # Act
        result = await use_case(input_dto)
        order_id = result.unwrap().order_id
        
        # Assert
        saved_order = await use_case.order_repo.get(order_id)
        assert saved_order is not None
        assert saved_order.customer_id == "customer-1"
    
    async def test_create_order_publishes_events(self, use_case):
        """测试创建订单发布事件"""
        # Arrange
        event_spy = EventSpy()
        use_case.uow.event_bus = event_spy
        
        input_dto = CreateOrderInput(
            customer_id="customer-1",
            items=[{"product_id": "p1", "quantity": 1, "unit_price": 100}]
        )
        
        # Act
        await use_case(input_dto)
        
        # Assert
        assert event_spy.published_count == 1
        assert event_spy.events[0].event_type == "order.created.v1"
    
    async def test_create_order_with_empty_items_fails(self, use_case):
        """测试空订单项创建失败"""
        # Arrange
        input_dto = CreateOrderInput(
            customer_id="customer-1",
            items=[]
        )
        
        # Act
        result = await use_case(input_dto)
        
        # Assert
        assert result.is_err
        assert "empty" in result.unwrap_err().lower()
```

### Core 层测试

```python
# tests/unit/core/test_result.py
from bento.core.result import Result, Ok, Err

class TestResult:
    """Result 类型测试"""
    
    def test_ok_result_is_ok(self):
        result = Ok(42)
        assert result.is_ok is True
        assert result.is_err is False
    
    def test_err_result_is_err(self):
        result = Err("error message")
        assert result.is_ok is False
        assert result.is_err is True
    
    def test_unwrap_ok_returns_value(self):
        result = Ok(42)
        assert result.unwrap() == 42
    
    def test_unwrap_err_raises_exception(self):
        result = Err("error")
        with pytest.raises(RuntimeError, match="error"):
            result.unwrap()
    
    def test_unwrap_err_returns_error(self):
        result = Err("error message")
        assert result.unwrap_err() == "error message"
    
    def test_map_transforms_ok_value(self):
        result = Ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.unwrap() == 10
    
    def test_map_leaves_err_unchanged(self):
        result = Err("error")
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err
        assert mapped.unwrap_err() == "error"
```

---

## 集成测试

### 原则

1. **真实组件**: 使用真实的基础设施（数据库、消息队列等）
2. **隔离环境**: 使用测试数据库/容器
3. **清理**: 每个测试后清理数据
4. **速度**: 控制在 1 秒内

### 数据库集成测试

```python
# tests/integration/persistence/test_order_repository.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from bento.persistence.sqlalchemy import SQLAlchemyOrderRepository, Base
from bento.domain.order import Order

@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    # 使用 SQLite 内存数据库
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
    
    # 清理
    await engine.dispose()

@pytest.fixture
def order_repo(db_session):
    """创建订单仓储"""
    return SQLAlchemyOrderRepository(session=db_session)

class TestSQLAlchemyOrderRepository:
    """SQLAlchemy 订单仓储集成测试"""
    
    async def test_save_and_get_order(self, order_repo):
        """测试保存和获取订单"""
        # Arrange
        order = Order.create(customer_id="customer-1")
        order.add_item("product-1", 2, Money(Decimal("100"), "USD"))
        
        # Act
        await order_repo.save(order)
        retrieved = await order_repo.get(order.id)
        
        # Assert
        assert retrieved is not None
        assert retrieved.id == order.id
        assert retrieved.customer_id == "customer-1"
        assert len(retrieved.items) == 1
        assert retrieved.total == Money(Decimal("200"), "USD")
    
    async def test_get_nonexistent_order_returns_none(self, order_repo):
        """测试获取不存在的订单返回 None"""
        # Act
        order = await order_repo.get(EntityId("nonexistent-id"))
        
        # Assert
        assert order is None
    
    async def test_list_orders_by_customer(self, order_repo):
        """测试按客户查询订单"""
        # Arrange
        order1 = Order.create(customer_id="customer-1")
        order2 = Order.create(customer_id="customer-1")
        order3 = Order.create(customer_id="customer-2")
        
        await order_repo.save(order1)
        await order_repo.save(order2)
        await order_repo.save(order3)
        
        # Act
        customer1_orders = await order_repo.find_by_customer("customer-1")
        
        # Assert
        assert len(customer1_orders) == 2
        assert all(o.customer_id == "customer-1" for o in customer1_orders)
```

### UnitOfWork 集成测试

```python
# tests/integration/persistence/test_unit_of_work.py
@pytest.mark.asyncio
class TestSQLAlchemyUnitOfWork:
    """UnitOfWork 集成测试"""
    
    async def test_commit_saves_changes(self, db_session):
        """测试提交保存变更"""
        # Arrange
        uow = SQLAlchemyUnitOfWork(session=db_session)
        order = Order.create("customer-1")
        
        # Act
        async with uow:
            uow.order_repo.add(order)
            await uow.commit()
        
        # Assert
        retrieved = await db_session.get(OrderModel, order.id.value)
        assert retrieved is not None
    
    async def test_rollback_discards_changes(self, db_session):
        """测试回滚丢弃变更"""
        # Arrange
        uow = SQLAlchemyUnitOfWork(session=db_session)
        order = Order.create("customer-1")
        
        # Act
        async with uow:
            uow.order_repo.add(order)
            await uow.rollback()
        
        # Assert
        retrieved = await db_session.get(OrderModel, order.id.value)
        assert retrieved is None
    
    async def test_exception_triggers_rollback(self, db_session):
        """测试异常触发回滚"""
        # Arrange
        uow = SQLAlchemyUnitOfWork(session=db_session)
        order = Order.create("customer-1")
        
        # Act
        with pytest.raises(Exception):
            async with uow:
                uow.order_repo.add(order)
                raise Exception("Simulated error")
        
        # Assert
        retrieved = await db_session.get(OrderModel, order.id.value)
        assert retrieved is None
```

### Outbox 集成测试

```python
# tests/integration/messaging/test_outbox.py
@pytest.mark.asyncio
class TestOutboxPattern:
    """Outbox 模式集成测试"""
    
    async def test_events_saved_to_outbox_on_commit(self, db_session):
        """测试提交时事件保存到 Outbox"""
        # Arrange
        uow = SQLAlchemyUnitOfWork(session=db_session)
        order = Order.create("customer-1")
        
        # Act
        async with uow:
            uow.track(order)
            await uow.commit()
        
        # Assert
        outbox_messages = await db_session.execute(
            select(OutboxModel).where(OutboxModel.published == False)
        )
        messages = outbox_messages.scalars().all()
        
        assert len(messages) == 1
        assert messages[0].event_type == "order.created.v1"
        assert messages[0].aggregate_id == order.id.value
    
    async def test_outbox_publisher_publishes_events(
        self,
        db_session,
        event_bus_spy,
    ):
        """测试 Outbox 发布器发布事件"""
        # Arrange
        # 先保存一些未发布的事件
        outbox_message = OutboxModel(
            event_type="order.created.v1",
            aggregate_id="order-123",
            payload={"order_id": "order-123"},
            published=False,
        )
        db_session.add(outbox_message)
        await db_session.commit()
        
        publisher = OutboxPublisher(
            outbox_repo=SQLAlchemyOutboxRepository(db_session),
            event_bus=event_bus_spy,
        )
        
        # Act
        await publisher._publish_batch()
        
        # Assert
        assert event_bus_spy.published_count == 1
        
        # 检查标记为已发布
        await db_session.refresh(outbox_message)
        assert outbox_message.published is True
        assert outbox_message.published_at is not None
```

---

## 端到端测试

### 原则

1. **完整流程**: 从 HTTP 请求到数据库
2. **真实环境**: 使用完整的技术栈
3. **用户视角**: 测试真实用户场景
4. **关键路径**: 只测试核心业务流程

### API 端到端测试

```python
# tests/e2e/api/test_order_api.py
import pytest
from httpx import AsyncClient
from bento.interfaces.http import create_app

@pytest.fixture
async def client():
    """创建测试客户端"""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def db():
    """创建测试数据库"""
    # 设置测试数据库
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

class TestOrderAPI:
    """订单 API 端到端测试"""
    
    async def test_create_order_flow(self, client, db):
        """测试创建订单完整流程"""
        # Step 1: 创建订单
        response = await client.post("/api/orders", json={
            "customer_id": "customer-1",
            "items": [
                {"product_id": "p1", "quantity": 2, "unit_price": 100.00},
                {"product_id": "p2", "quantity": 1, "unit_price": 50.00},
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        order_id = data["order_id"]
        assert data["total_amount"] == 250.00
        assert data["status"] == "pending"
        
        # Step 2: 获取订单详情
        response = await client.get(f"/api/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == order_id
        assert len(data["items"]) == 2
        
        # Step 3: 确认订单
        response = await client.post(f"/api/orders/{order_id}/confirm")
        assert response.status_code == 200
        
        # Step 4: 验证状态变更
        response = await client.get(f"/api/orders/{order_id}")
        assert response.json()["status"] == "confirmed"
        
        # Step 5: 验证数据库
        async with db.begin() as conn:
            result = await conn.execute(
                select(OrderModel).where(OrderModel.id == order_id)
            )
            order_model = result.scalar_one()
            assert order_model.status == "confirmed"
    
    async def test_create_and_cancel_order(self, client, db):
        """测试创建并取消订单"""
        # 创建订单
        response = await client.post("/api/orders", json={
            "customer_id": "customer-1",
            "items": [{"product_id": "p1", "quantity": 1, "unit_price": 100}]
        })
        order_id = response.json()["order_id"]
        
        # 取消订单
        response = await client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "Customer request"}
        )
        assert response.status_code == 200
        
        # 验证无法确认已取消的订单
        response = await client.post(f"/api/orders/{order_id}/confirm")
        assert response.status_code == 400
        assert "Cannot confirm" in response.json()["error"]
```

### 业务场景测试

```python
# tests/e2e/scenarios/test_order_fulfillment.py
@pytest.mark.e2e
class TestOrderFulfillmentScenario:
    """订单履行场景测试"""
    
    async def test_complete_order_fulfillment(
        self,
        client,
        db,
        event_bus,
    ):
        """测试完整的订单履行流程"""
        
        # === 场景：客户下单并完成购买 ===
        
        # 1. 客户创建订单
        create_response = await client.post("/api/orders", json={
            "customer_id": "customer-1",
            "items": [
                {"product_id": "p1", "quantity": 2, "unit_price": 100.00}
            ]
        })
        order_id = create_response.json()["order_id"]
        
        # 验证事件：OrderCreatedEvent
        await self._assert_event_published(
            event_bus,
            "order.created.v1",
            {"order_id": order_id}
        )
        
        # 2. 客户确认订单
        await client.post(f"/api/orders/{order_id}/confirm")
        
        # 验证事件：OrderConfirmedEvent
        await self._assert_event_published(
            event_bus,
            "order.confirmed.v1",
            {"order_id": order_id}
        )
        
        # 3. 系统预留库存（事件处理器）
        await self._wait_for_event_processing()
        
        inventory = await self._get_inventory(db, "p1")
        assert inventory.reserved == 2
        
        # 4. 处理支付
        payment_response = await client.post(f"/api/payments", json={
            "order_id": order_id,
            "amount": 200.00,
            "method": "credit_card",
        })
        payment_id = payment_response.json()["payment_id"]
        
        # 5. 发货
        await client.post(f"/api/shipments", json={
            "order_id": order_id,
            "carrier": "SF Express",
        })
        
        # 6. 验证最终状态
        final_order = await self._get_order(db, order_id)
        assert final_order.status == "shipped"
        
        final_inventory = await self._get_inventory(db, "p1")
        assert final_inventory.quantity == 98  # 100 - 2
        assert final_inventory.reserved == 0    # 已发货，释放预留
```

---

## 测试工具与技巧

### Pytest 配置

```python
# pytest.ini
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# 标记
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
]

# 异步支持
asyncio_mode = "auto"

# 覆盖率
addopts = [
    "-v",
    "--strict-markers",
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
]
```

### 参数化测试

```python
import pytest
from decimal import Decimal

@pytest.mark.parametrize("amount,currency,expected", [
    (Decimal("100"), "USD", "100.00 USD"),
    (Decimal("50.5"), "EUR", "50.50 EUR"),
    (Decimal("0"), "CNY", "0.00 CNY"),
])
def test_money_display(amount, currency, expected):
    """参数化测试金额显示"""
    money = Money(amount, currency)
    assert str(money) == expected

@pytest.mark.parametrize("status,can_cancel", [
    (OrderStatus.PENDING, True),
    (OrderStatus.CONFIRMED, True),
    (OrderStatus.SHIPPED, False),
    (OrderStatus.DELIVERED, False),
    (OrderStatus.CANCELLED, False),
])
def test_order_cancellation_rules(status, can_cancel):
    """参数化测试订单取消规则"""
    order = Order.create("customer-1")
    order.status = status
    
    assert order.can_be_cancelled() == can_cancel
```

### 测试标记

```python
# 标记慢测试
@pytest.mark.slow
async def test_large_batch_processing():
    ...

# 标记集成测试
@pytest.mark.integration
async def test_database_integration():
    ...

# 标记端到端测试
@pytest.mark.e2e
async def test_complete_flow():
    ...

# 跳过测试
@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    ...

# 条件跳过
@pytest.mark.skipif(sys.version_info < (3, 11), reason="Requires Python 3.11+")
def test_new_syntax():
    ...
```

### 运行特定测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 排除慢测试
pytest -m "not slow"

# 运行特定文件
pytest tests/unit/domain/test_order.py

# 运行特定测试类
pytest tests/unit/domain/test_order.py::TestOrderCreation

# 运行特定测试方法
pytest tests/unit/domain/test_order.py::TestOrderCreation::test_create_order

# 并行运行（需要 pytest-xdist）
pytest -n auto
```

---

## Fixture 管理

### Fixture 组织

```python
# tests/conftest.py - 全局 fixture
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    """创建数据库引擎（会话级别）"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """创建数据库会话（函数级别）"""
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()

# tests/unit/conftest.py - 单元测试 fixture
@pytest.fixture
def sample_order():
    """示例订单"""
    order = Order.create("customer-1")
    order.add_item("product-1", 2, Money(Decimal("100"), "USD"))
    return order

# tests/integration/conftest.py - 集成测试 fixture
@pytest.fixture
async def order_repo(db_session):
    """订单仓储"""
    return SQLAlchemyOrderRepository(session=db_session)
```

### Fixture 作用域

```python
@pytest.fixture(scope="function")  # 默认，每个测试函数创建
def temp_data():
    ...

@pytest.fixture(scope="class")  # 每个测试类创建一次
def shared_resource():
    ...

@pytest.fixture(scope="module")  # 每个模块创建一次
def module_setup():
    ...

@pytest.fixture(scope="session")  # 整个测试会话创建一次
def database():
    ...
```

### Factory Fixture

```python
@pytest.fixture
def order_factory():
    """订单工厂 fixture"""
    def _create_order(
        customer_id: str = "customer-1",
        items: Optional[List[dict]] = None,
    ) -> Order:
        order = Order.create(customer_id)
        
        if items:
            for item in items:
                order.add_item(
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    unit_price=Money(Decimal(item["price"]), "USD")
                )
        
        return order
    
    return _create_order

# 使用
def test_something(order_factory):
    order1 = order_factory()
    order2 = order_factory(customer_id="customer-2")
    order3 = order_factory(items=[{"product_id": "p1", "quantity": 5, "price": 100}])
```

---

## Mock 与 Stub

### 测试替身类型

```python
# 1. Dummy - 只为了满足参数，不会被使用
class DummyEventBus:
    async def publish(self, topic, payload):
        pass

# 2. Stub - 返回预设值
class StubOrderRepository:
    async def get(self, order_id):
        return Order.create("customer-1")  # 固定返回

# 3. Spy - 记录调用
class EventBusSpy:
    def __init__(self):
        self.events = []
        self.published_count = 0
    
    async def publish(self, topic, payload):
        self.events.append((topic, payload))
        self.published_count += 1

# 4. Mock - 验证行为
from unittest.mock import AsyncMock, MagicMock

mock_repo = AsyncMock()
mock_repo.save.return_value = None
await mock_repo.save(order)
mock_repo.save.assert_called_once_with(order)

# 5. Fake - 真实实现的简化版
class InMemoryOrderRepository:
    def __init__(self):
        self._storage = {}
    
    async def save(self, order):
        self._storage[order.id.value] = order
    
    async def get(self, order_id):
        return self._storage.get(order_id.value)
```

### 使用 Mock

```python
from unittest.mock import AsyncMock, patch

async def test_order_creation_with_mock():
    """使用 Mock 测试"""
    # Arrange
    mock_repo = AsyncMock()
    mock_uow = AsyncMock()
    
    use_case = CreateOrder(order_repo=mock_repo, uow=mock_uow)
    
    # Act
    input_dto = CreateOrderInput(customer_id="customer-1", items=[...])
    result = await use_case(input_dto)
    
    # Assert
    assert result.is_ok
    mock_repo.save.assert_called_once()
    mock_uow.commit.assert_called_once()

# 使用 patch
@patch('bento.infrastructure.email.EmailService')
async def test_send_order_confirmation(mock_email):
    """测试发送订单确认邮件"""
    # Arrange
    mock_email.send.return_value = True
    
    # Act
    await send_order_confirmation(order_id="123")
    
    # Assert
    mock_email.send.assert_called_once_with(
        to="customer@example.com",
        subject="Order Confirmation",
        body=unittest.mock.ANY,
    )
```

### 推荐：优先使用 Fake

```python
# ✅ 推荐 - 使用 Fake（InMemory 实现）
class TestCreateOrder:
    @pytest.fixture
    def use_case(self):
        return CreateOrder(
            order_repo=InMemoryOrderRepository(),
            uow=InMemoryUnitOfWork(),
        )
    
    async def test_create_order(self, use_case):
        result = await use_case(CreateOrderInput(...))
        assert result.is_ok

# ❌ 不推荐 - 过度使用 Mock
class TestCreateOrder:
    async def test_create_order(self):
        mock_repo = AsyncMock()
        mock_uow = AsyncMock()
        mock_repo.save = AsyncMock(return_value=None)
        mock_uow.commit = AsyncMock(return_value=None)
        # ... 大量 Mock 配置
```

**原因**：
- Fake 测试真实行为
- Mock 测试实现细节
- Fake 重构友好
- Mock 容易过度耦合

---

## 测试数据

### 测试数据构建器

```python
# tests/builders.py
class OrderBuilder:
    """订单构建器"""
    
    def __init__(self):
        self._customer_id = "customer-1"
        self._items = []
        self._status = OrderStatus.PENDING
    
    def with_customer(self, customer_id: str) -> "OrderBuilder":
        self._customer_id = customer_id
        return self
    
    def with_item(
        self,
        product_id: str,
        quantity: int,
        price: Decimal,
    ) -> "OrderBuilder":
        self._items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": price,
        })
        return self
    
    def with_status(self, status: OrderStatus) -> "OrderBuilder":
        self._status = status
        return self
    
    def build(self) -> Order:
        order = Order.create(self._customer_id)
        for item in self._items:
            order.add_item(
                item["product_id"],
                item["quantity"],
                Money(item["price"], "USD")
            )
        order.status = self._status
        return order

# 使用
def test_high_value_order():
    order = (
        OrderBuilder()
        .with_customer("vip-customer")
        .with_item("luxury-item", 1, Decimal("10000"))
        .with_status(OrderStatus.CONFIRMED)
        .build()
    )
    
    assert order.total.amount >= 10000
```

### Object Mother 模式

```python
# tests/object_mothers.py
class OrderMother:
    """订单对象母亲"""
    
    @staticmethod
    def create_empty_pending_order(customer_id: str = "customer-1") -> Order:
        """创建空的待处理订单"""
        return Order.create(customer_id)
    
    @staticmethod
    def create_standard_order() -> Order:
        """创建标准订单"""
        order = Order.create("customer-1")
        order.add_item("product-1", 2, Money(Decimal("100"), "USD"))
        order.add_item("product-2", 1, Money(Decimal("50"), "USD"))
        return order
    
    @staticmethod
    def create_high_value_order() -> Order:
        """创建高价值订单"""
        order = Order.create("vip-customer")
        order.add_item("luxury-1", 1, Money(Decimal("5000"), "USD"))
        order.add_item("luxury-2", 1, Money(Decimal("3000"), "USD"))
        return order
    
    @staticmethod
    def create_confirmed_order() -> Order:
        """创建已确认订单"""
        order = OrderMother.create_standard_order()
        order.confirm()
        return order

# 使用
def test_cancel_confirmed_order():
    order = OrderMother.create_confirmed_order()
    result = order.cancel(reason="Customer request")
    assert result.is_ok
```

---

## 性能测试

### 基准测试

```python
import pytest
import time

@pytest.mark.benchmark
def test_order_creation_performance(benchmark):
    """基准测试订单创建性能"""
    def create_order():
        order = Order.create("customer-1")
        for i in range(10):
            order.add_item(f"product-{i}", 1, Money(Decimal("100"), "USD"))
        return order
    
    result = benchmark(create_order)
    assert len(result.items) == 10

# 运行: pytest --benchmark-only
```

### 负载测试

```python
@pytest.mark.load
async def test_concurrent_order_creation():
    """并发创建订单负载测试"""
    async def create_order_task(i):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/orders",
                json={"customer_id": f"customer-{i}", "items": [...]}
            )
            return response.status_code
    
    # 并发 100 个请求
    tasks = [create_order_task(i) for i in range(100)]
    results = await asyncio.gather(*tasks)
    
    # 验证成功率
    success_count = sum(1 for r in results if r == 201)
    assert success_count >= 95  # 95% 成功率
```

---

## 快速检查清单

### 测试质量
- [ ] 测试名称清晰表达意图
- [ ] 每个测试只测一件事
- [ ] 使用 Arrange-Act-Assert 模式
- [ ] 测试快速（单元测试 < 100ms）
- [ ] 测试独立（顺序无关）

### 覆盖率
- [ ] Domain 层 > 90%
- [ ] Application 层 > 80%
- [ ] 关键路径 100%
- [ ] 边界条件覆盖
- [ ] 错误处理覆盖

### 测试类型
- [ ] 单元测试（70%）
- [ ] 集成测试（20%）
- [ ] E2E 测试（10%）
- [ ] 性能测试（关键路径）

### 最佳实践
- [ ] 优先使用 Fake 而非 Mock
- [ ] 使用 Builder/Object Mother 构建测试数据
- [ ] 清理测试数据
- [ ] 使用测试标记分类
- [ ] CI/CD 自动运行

---

## 参考资料

- [Pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
- [Testing Strategies](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html)


