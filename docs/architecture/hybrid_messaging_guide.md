# Hybrid Messaging 架构指南

## 🎯 概述

HybridMessageBus 提供智能事件路由，根据业务上下文和性能需求自动选择最优的发布策略。

## 🚀 核心优势

### 1. 智能路由
- **进程内发布**: 同一BC内的快速响应 (<10ms)
- **跨BC发布**: 不同BC间的可靠传递 (50-500ms)
- **自动选择**: 基于事件类型和业务上下文

### 2. 多种策略
- `SYNC_ONLY`: 纯同步发布，最低延迟
- `ASYNC_ONLY`: 纯异步发布，最高可靠性
- `HYBRID_FAST`: 同步优先，失败时异步兜底
- `HYBRID_RELIABLE`: 异步保证，同步确认

### 3. 业务感知
- 按事件类型配置策略
- 按Bounded Context设置默认策略
- 运行时策略覆盖

## 📋 使用场景

### 进程内快速响应
```python
# UI状态更新 - 需要立即反馈
@dataclass(frozen=True)
class OrderStatusUpdatedEvent(DomainEvent):
    topic: str = "order.status_updated"
    bounded_context: str = "orders"

# 配置为快速同步发布
bus.configure_event(OrderStatusUpdatedEvent, PublishStrategies.INTRA_BC_FAST)
```

### 跨BC可靠传递
```python
# 订单创建 - 影响多个BC，必须可靠
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    topic: str = "order.created"
    bounded_context: str = "orders"

# 配置为混合可靠策略
bus.configure_event(OrderCreatedEvent, PublishStrategies.CRITICAL_HYBRID)
```

## 🔧 配置指南

### 1. 基础设置

```python
from bento.adapters.messaging.hybrid.message_bus import DefaultHybridMessageBus
from bento.adapters.messaging.inprocess.message_bus import InProcessMessageBus
from bento.persistence.outbox.record import SqlAlchemyOutbox

# 创建HybridMessageBus
hybrid_bus = DefaultHybridMessageBus(
    sync_bus=InProcessMessageBus(source="app"),
    async_outbox=SqlAlchemyOutbox(session)
)
```

### 2. 事件级别配置

```python
# 关键业务事件
bus.configure_event(OrderCreatedEvent, PublishConfig(
    strategy=PublishStrategy.HYBRID_RELIABLE,  # 异步+同步确认
    scope=EventScope.INTER_BC,
    timeout_ms=200,
    priority=9
))

# 快速反馈事件
bus.configure_event(UINotificationEvent, PublishConfig(
    strategy=PublishStrategy.HYBRID_FAST,      # 同步+异步兜底
    scope=EventScope.INTRA_BC,
    timeout_ms=50,
    priority=5
))
```

### 3. BC级别配置

```python
# 订单域 - 关键业务，混合策略
bus.configure_bounded_context("orders", PublishStrategies.CRITICAL_HYBRID)

# 库存域 - 跨系统集成，异步可靠
bus.configure_bounded_context("inventory", PublishStrategies.INTER_BC_RELIABLE)

# 前端域 - 用户体验优先，快速同步
bus.configure_bounded_context("frontend", PublishStrategies.INTRA_BC_FAST)
```

## 📊 策略选择指南

| 场景 | 延迟要求 | 可靠性要求 | 推荐策略 |
|------|----------|------------|----------|
| UI状态更新 | <10ms | 中 | `SYNC_ONLY` |
| 实时通知 | <50ms | 中 | `HYBRID_FAST` |
| 业务事件 | <200ms | 高 | `HYBRID_RELIABLE` |
| 跨系统集成 | <1s | 极高 | `ASYNC_ONLY` |

## 🎯 最佳实践

### 1. 按业务重要性分级

```python
# P0: 核心业务流程
OrderCreatedEvent -> HYBRID_RELIABLE
PaymentProcessedEvent -> HYBRID_RELIABLE

# P1: 重要但非核心
InventoryUpdatedEvent -> ASYNC_ONLY
EmailSentEvent -> ASYNC_ONLY

# P2: 用户体验相关
UINotificationEvent -> HYBRID_FAST
StatusUpdatedEvent -> SYNC_ONLY
```

### 2. 按Bounded Context边界

```python
# 同BC内: 优先同步，快速响应
INTRA_BC -> SYNC_ONLY or HYBRID_FAST

# 跨BC: 优先异步，保证可靠性
INTER_BC -> ASYNC_ONLY or HYBRID_RELIABLE

# 外部系统: 纯异步，容错性优先
EXTERNAL -> ASYNC_ONLY
```

### 3. 监控和调优

```python
# 获取性能指标
metrics = await bus.get_metrics()

# 根据指标调整策略
if metrics["failure_rate"] > "5%":
    # 增加超时时间或切换到更可靠策略
    pass

if metrics["hybrid_fast_fallbacks"] > 50:
    # 考虑直接使用异步策略
    pass
```

## 🚨 故障处理

### 1. 熔断器机制
- 自动检测故障并触发熔断
- 60秒后自动重置
- 保护系统稳定性

### 2. 降级策略
```python
# 同步失败时自动降级到异步
HYBRID_FAST: sync_fail -> async_fallback

# 保证至少有一种方式能成功
HYBRID_RELIABLE: async_first -> sync_confirm (optional)
```

### 3. 监控告警
```python
# 关键指标监控
- failure_rate > 5%: 告警
- circuit_breaker_trips > 0: 告警
- avg_latency > 500ms: 警告
```

## 💡 使用建议

### ✅ 适合使用HybridMessageBus的场景
- 有明确的进程内和跨进程发布需求
- 不同事件有不同的延迟和可靠性要求
- 需要根据业务上下文智能路由
- 希望获得详细的发布指标和监控

### ⚠️ 不需要HybridMessageBus的场景
- 所有事件都有相同的发布要求
- 系统规模较小，复杂性不值得
- 已有稳定的发布机制且无明显问题

## 🎉 总结

HybridMessageBus为您的场景量身定制：
- **进程内发布**: 快速响应用户操作
- **跨BC发布**: 可靠的业务数据同步
- **智能路由**: 自动选择最优策略
- **完整监控**: 性能可观测和调优

这正是您需要的messaging解决方案！
