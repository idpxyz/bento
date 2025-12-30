"""端到端集成测试 - 完整的Outbox + MessageBus + OutboxProjector流程

这个测试覆盖了完整的事件发布流程：
1. Domain Event → UoW → OutboxRecord (事务性存储)
2. OutboxProjector → MessageBus (异步发布)
3. 配置外部化 → 性能模板 → 验证系统
4. 错误处理 → 重试机制 → 死信处理
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bento.adapters.messaging.inprocess.message_bus import InProcessMessageBus
from bento.config.outbox import OutboxProjectorConfig
from bento.config.templates import ConfigTemplates
from bento.config.validation import ConfigValidator
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event
from bento.infrastructure.projection.projector import OutboxProjector
from bento.persistence.outbox.record import OutboxRecord
from bento.persistence.po.base import Base

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 测试事件定义 - 使用dataclass方式，先定义再注册
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """测试事件：订单创建"""

    order_id: str = ""
    customer_id: str = ""
    amount: float = 0.0


@dataclass(frozen=True)
class PaymentProcessedEvent(DomainEvent):
    """测试事件：支付处理"""

    payment_id: str = ""
    order_id: str = ""
    status: str = ""


# 注册事件类（在类定义之后）
register_event(OrderCreatedEvent)
register_event(PaymentProcessedEvent)


class TestMessageBusCollector(InProcessMessageBus):
    """测试专用MessageBus，收集发布的事件"""

    def __init__(self):
        super().__init__(source="test-collector")
        self.published_events: list[DomainEvent] = []
        self.publish_calls = 0

    async def publish(self, event: DomainEvent | list[DomainEvent]) -> None:
        """收集发布的事件"""
        await super().publish(event)  # 调用父类方法

        self.publish_calls += 1
        events = event if isinstance(event, list) else [event]
        self.published_events.extend(events)

        logger.info(f"📡 MessageBus收到 {len(events)} 个事件，总计: {len(self.published_events)}")


@pytest_asyncio.fixture
async def database_engine():
    """创建测试数据库引擎"""
    # 使用内存SQLite进行测试
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url, echo=False)

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(database_engine):
    """创建Session工厂"""
    return async_sessionmaker(database_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def message_bus():
    """创建测试MessageBus"""
    bus = TestMessageBusCollector()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def test_config():
    """创建测试配置 - 针对测试优化"""
    return OutboxProjectorConfig(
        batch_size=10,
        max_retry_attempts=3,
        sleep_busy=0.001,  # 快速轮询用于测试
        sleep_idle=0.01,
        default_tenant_id="test_tenant",
        # 测试环境使用极短的退避延迟
        backoff_base_seconds=0,  # 0秒基础延迟，立即重试
        backoff_multiplier=1,
    )


class TestOutboxEndToEnd:
    """端到端集成测试套件"""

    @pytest.mark.asyncio
    async def test_basic_event_flow(self, session_factory, message_bus, test_config):
        """测试基本事件流程：Outbox → Projector → MessageBus"""

        # 1. 直接添加事件到Outbox
        async with session_factory() as session:
            # 创建测试事件 - 使用业务友好的topic
            event1 = OrderCreatedEvent(
                event_id=uuid4(),
                topic="order.created",  # 业务友好的topic，自动映射到类
                occurred_at=datetime.now(UTC),
                tenant_id="test_tenant",
                order_id="order-123",
                customer_id="customer-456",
                amount=99.99,
            )
            event2 = PaymentProcessedEvent(
                event_id=uuid4(),
                topic="payment.processed",  # 业务友好的topic
                occurred_at=datetime.now(UTC),
                tenant_id="test_tenant",
                payment_id="pay-789",
                order_id="order-123",
                status="completed",
            )

            # 创建OutboxRecord并添加到数据库
            record1 = OutboxRecord.from_domain_event(event1)
            record2 = OutboxRecord.from_domain_event(event2)

            session.add(record1)
            session.add(record2)

            # 提交事务
            await session.commit()

        # 2. 验证事件已存储在Outbox中
        async with session_factory() as session:
            stmt = select(OutboxRecord).where(OutboxRecord.tenant_id == "test_tenant")
            result = await session.execute(stmt)
            records = result.scalars().all()

            assert len(records) == 2, f"应该有2个Outbox记录，实际: {len(records)}"

            topics = [r.topic for r in records]
            assert "order.created" in topics
            assert "payment.processed" in topics

        logger.info("✅ 步骤1: 事件成功存储到Outbox")

        # 3. 启动OutboxProjector处理事件
        projector = OutboxProjector(
            session_factory=session_factory,
            message_bus=message_bus,
            tenant_id="test_tenant",  # 明确指定tenant_id
            config=test_config,
        )

        # 处理所有待发布事件
        processed_count = await projector.publish_all()

        assert processed_count == 2, f"应该处理2个事件，实际: {processed_count}"
        assert len(message_bus.published_events) == 2, "MessageBus应该收到2个事件"

        logger.info("✅ 步骤2: OutboxProjector成功发布事件")

        # 4. 验证事件状态更新
        async with session_factory() as session:
            stmt = select(OutboxRecord).where(OutboxRecord.tenant_id == "test_tenant")
            result = await session.execute(stmt)
            records = result.scalars().all()

            sent_count = sum(1 for r in records if r.status == "SENT")
            assert sent_count == 2, f"应该有2个SENT状态记录，实际: {sent_count}"

        logger.info("✅ 步骤3: Outbox记录状态正确更新")

        # 5. 验证发布的事件内容
        published_topics = [e.topic for e in message_bus.published_events]
        assert "order.created" in published_topics
        assert "payment.processed" in published_topics

        logger.info("✅ 端到端流程测试通过")

    @pytest.mark.asyncio
    async def test_configuration_templates_integration(self, session_factory, message_bus):
        """测试配置模板集成"""

        # 测试不同性能场景的配置模板
        scenarios = [
            ("development", "开发环境"),
            ("production", "生产环境"),
            ("high_throughput", "高吞吐量"),
            ("low_latency", "低延迟"),
        ]

        for template_name, desc in scenarios:
            config = ConfigTemplates.get_template(template_name)

            # 验证配置
            validator = ConfigValidator()
            result = validator.validate(config)

            assert result.is_valid, (
                f"{desc}配置应该有效，错误: {[e.message for e in result.errors]}"
            )

            # 创建Projector验证配置可用性
            projector = OutboxProjector(
                session_factory=session_factory,
                message_bus=message_bus,
                config=config,
            )

            assert projector._config.batch_size == config.batch_size
            assert projector._tenant_id == config.default_tenant_id

            logger.info(f"✅ {desc}配置模板集成测试通过")

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self, session_factory, test_config):
        """测试错误处理和重试机制"""

        # 创建会失败的MessageBus
        class FailingMessageBus:
            def __init__(self, fail_count: int = 2):
                self.fail_count = fail_count
                self.attempt_count = 0
                self.published_events: list[DomainEvent] = []

            async def publish(self, event: DomainEvent | list[DomainEvent]) -> None:
                self.attempt_count += 1
                if self.attempt_count <= self.fail_count:
                    raise RuntimeError(f"模拟发布失败 (尝试 {self.attempt_count})")

                # 第3次尝试成功
                events = event if isinstance(event, list) else [event]
                self.published_events.extend(events)
                logger.info(f"📡 第{self.attempt_count}次尝试发布成功")

            # 添加MessageBus协议要求的方法
            async def subscribe(self, *args, **kwargs):
                pass

            async def unsubscribe(self, *args, **kwargs):
                pass

            async def start(self):
                pass

            async def stop(self):
                pass

        failing_bus = FailingMessageBus(fail_count=2)

        # 1. 创建事件存储到Outbox
        async with session_factory() as session:
            event = OrderCreatedEvent(
                event_id=uuid4(),
                topic="order.created",
                occurred_at=datetime.now(UTC),
                tenant_id="test_tenant",
                order_id="retry-order",
                customer_id="retry-customer",
                amount=50.0,
            )
            record = OutboxRecord.from_domain_event(event)
            session.add(record)
            await session.commit()

        # 验证事件已创建
        async with session_factory() as session:
            stmt = select(OutboxRecord).where(OutboxRecord.topic == "order.created")
            result = await session.execute(stmt)
            test_record = result.scalar_one()
            logger.info(
                f"Event created: status={test_record.status}, retry_count={test_record.retry_count}"
            )

        # 2. 创建Projector并尝试发布
        projector = OutboxProjector(
            session_factory=session_factory,
            message_bus=failing_bus,
            tenant_id="test_tenant",
            config=test_config,
        )

        # 简化的重试逻辑：多次调用直到成功
        # FailingMessageBus前2次失败，第3次开始成功
        for i in range(5):  # 最多5次尝试
            has_events = await projector._process_once()
            logger.info(
                f"Attempt {i + 1}: has_events={has_events}, "
                f"bus.attempt_count={failing_bus.attempt_count}, "
                f"published={len(failing_bus.published_events)}"
            )
            if len(failing_bus.published_events) > 0:
                logger.info(f"✅ 第{i + 1}次尝试后发布成功")
                break

        # 验证最终结果
        assert len(failing_bus.published_events) >= 1, (
            f"应该有事件被发布，但只有{len(failing_bus.published_events)}个事件，"
            f"尝试次数={failing_bus.attempt_count}"
        )
        assert failing_bus.attempt_count >= 3, "应该至少尝试3次"

        async with session_factory() as session:
            stmt = select(OutboxRecord).where(OutboxRecord.topic == "order.created")
            result = await session.execute(stmt)
            record = result.scalar_one()
            assert record.status == "SENT", f"Expected SENT, got {record.status}"

        logger.info("✅ 重试机制：最终发布成功")

    @pytest.mark.asyncio
    async def test_dead_letter_handling(self, session_factory, test_config):
        """测试死信处理"""

        # 创建永远失败的MessageBus
        class AlwaysFailingMessageBus:
            async def publish(self, event: DomainEvent | list[DomainEvent]) -> None:
                raise RuntimeError("永久发布失败")

            # 添加MessageBus协议要求的方法
            async def subscribe(self, *args, **kwargs):
                pass

            async def unsubscribe(self, *args, **kwargs):
                pass

            async def start(self):
                pass

            async def stop(self):
                pass

        always_failing_bus = AlwaysFailingMessageBus()

        # 创建事件
        async with session_factory() as session:
            event = OrderCreatedEvent(
                event_id=uuid4(),
                topic="order.created",
                occurred_at=datetime.now(UTC),
                tenant_id="test_tenant",
                order_id="dead-order",
                customer_id="dead-customer",
                amount=100.0,
            )
            record = OutboxRecord.from_domain_event(event)
            session.add(record)
            await session.commit()

        # 创建Projector
        projector = OutboxProjector(
            session_factory=session_factory,
            message_bus=always_failing_bus,
            tenant_id="test_tenant",
            config=test_config,  # max_retry_attempts=3
        )

        # 简化：直接多次调用，直到达到DEAD状态
        # max_retry_attempts=3，所以3次失败后应该变为DEAD
        for _ in range(test_config.max_retry_attempts + 2):
            await projector._process_once()

        # 验证事件被标记为DEAD
        async with session_factory() as session:
            stmt = select(OutboxRecord).where(OutboxRecord.topic == "order.created")
            result = await session.execute(stmt)
            record = result.scalar_one()

            assert record.status == "DEAD", f"Expected DEAD, got {record.status}"
            assert record.retry_count >= test_config.max_retry_attempts

        logger.info("✅ 死信处理：超过最大重试的事件正确标记为DEAD")

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, session_factory, message_bus, test_config):
        """测试多租户隔离"""

        # 为不同租户创建事件
        tenants = ["tenant_a", "tenant_b", "tenant_c"]

        async with session_factory() as session:
            for tenant in tenants:
                # 直接创建OutboxRecord，设置正确的tenant_id
                event = OrderCreatedEvent(
                    event_id=uuid4(),
                    topic="order.created",
                    occurred_at=datetime.now(UTC),
                    tenant_id=tenant,  # 直接设置正确的tenant_id
                    order_id=f"order-{tenant}",
                    customer_id=f"customer-{tenant}",
                    amount=75.0,
                )
                record = OutboxRecord.from_domain_event(event)
                session.add(record)

            await session.commit()

        # 为tenant_a创建专用Projector
        config_a = OutboxProjectorConfig(
            batch_size=5,
            default_tenant_id="tenant_a",
            sleep_busy=0.001,
        )

        projector_a = OutboxProjector(
            session_factory=session_factory,
            message_bus=message_bus,
            config=config_a,
        )

        # 处理tenant_a的事件
        processed = await projector_a.publish_all()

        # 应该只处理1个事件（tenant_a的）
        assert processed == 1
        assert len(message_bus.published_events) == 1
        assert message_bus.published_events[0].tenant_id == "tenant_a"

        # 验证其他租户的事件仍然是NEW状态
        async with session_factory() as session:
            stmt = select(OutboxRecord).where(OutboxRecord.tenant_id.in_(["tenant_b", "tenant_c"]))
            result = await session.execute(stmt)
            other_records = result.scalars().all()

            assert len(other_records) == 2
            assert all(r.status == "NEW" for r in other_records)

        logger.info("✅ 多租户隔离：Projector正确处理指定租户事件")

    def test_configuration_validation_integration(self):
        """测试配置验证集成"""

        # 测试有效配置
        valid_config = OutboxProjectorConfig(
            batch_size=100,
            sleep_busy=0.1,
            max_retry_attempts=5,
        )

        validator = ConfigValidator()
        result = validator.validate(valid_config)

        assert result.is_valid
        assert len(result.errors) == 0

        # 测试无效配置
        invalid_config = OutboxProjectorConfig(
            batch_size=50000,  # 超出范围
            sleep_busy=-1.0,  # 负值
            max_retry_attempts=200,  # 过大
        )

        result = validator.validate(invalid_config)

        assert not result.is_valid
        assert len(result.errors) >= 3  # 至少3个错误

        # 验证错误消息结构
        for error in result.errors:
            assert hasattr(error, "message")
            assert hasattr(error, "field_name")
            assert hasattr(error, "severity")
            assert error.severity == "error"

        logger.info("✅ 配置验证集成：正确识别有效和无效配置")


if __name__ == "__main__":
    # 运行基础流程测试
    async def run_basic_test():
        """运行基础端到端测试"""
        print("🚀 运行端到端集成测试")

        # 创建内存数据库
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # 创建MessageBus
        bus = TestMessageBusCollector()
        await bus.start()

        # 运行测试
        test_suite = TestOutboxEndToEnd()
        config = OutboxProjectorConfig(batch_size=5, sleep_busy=0.001)

        try:
            await test_suite.test_basic_event_flow(session_factory, bus, config)
            print("✅ 基础流程测试通过")

            await test_suite.test_configuration_templates_integration(session_factory, bus)
            print("✅ 配置模板集成测试通过")

            test_suite.test_configuration_validation_integration()
            print("✅ 配置验证集成测试通过")

        finally:
            await bus.stop()
            await engine.dispose()

        print("🎉 所有端到端测试通过！")

    asyncio.run(run_basic_test())
