# Bento Outbox 重构指南

## 🎯 **重构概述**

基于 DDD 六边形架构最佳实践，我们对 Outbox 模块进行了重构，将智能路由功能移到正确的架构层。

## 📊 **架构变更对比**

### ❌ **之前的错误架构**
```
Outbox (Persistence 层)
├── 复杂路由逻辑 ❌ (违反分层原则)
├── 数据转换 ❌ (不属于存储层职责)
├── 条件判断 ❌ (业务逻辑混入持久化层)
└── 事务性存储 ✅
```

### ✅ **现在的正确架构**
```
MessageBus (Application 层)
├── 智能路由 ✅ (正确的职责)
├── 条件判断 ✅
├── 数据转换 ✅
└── 多目标分发 ✅

OutboxProcessor (Infrastructure 层)
├── 可靠投递 ✅
├── 重试机制 ✅
└── 错误处理 ✅

Outbox (Persistence 层)
├── 事务性存储 ✅ (核心职责)
├── 状态管理 ✅
└── 简单路由键 ✅ (向下兼容)
```

## 🔄 **API 变更说明**

### **类名变更**

| 之前 | 现在 | 说明 |
|------|------|------|
| `SimpleOutboxProcessor` | `OutboxProcessor` | 成为主要的处理器类 |
| `create_simple_outbox_processor()` | `create_outbox_processor()` | 简化函数名 |
| ~~`OutboxProcessor`~~ | ❌ 已删除 | 复杂的路由处理器已移除 |

### **导入变更**

```python
# ✅ 现在的导入方式
from bento.persistence.outbox import (
    OutboxRecord,
    SqlAlchemyOutbox,
    OutboxProcessor,
    create_outbox_processor
)

# ❌ 之前的导入方式（已弃用）
from bento.persistence.outbox import (
    OutboxRecord,
    SqlAlchemyOutbox,
    SimpleOutboxProcessor,  # 已重命名
    create_simple_outbox_processor  # 已重命名
)
```

### **使用方式变更**

```python
# ✅ 现在的使用方式（推荐）
# 1. 创建智能消息总线
from bento.adapters.messaging.smart_message_bus import SmartMessageBus, configure_routing

base_bus = InProcessMessageBus()  # 或 PulsarMessageBus
smart_bus = SmartMessageBus(base_bus)

# 2. 配置智能路由（在 MessageBus 层）
configure_routing(smart_bus) \
    .for_event("OrderCreatedEvent") \
    .route_to("fulfillment") \
    .route_to("vip.notifications", conditions={"payload.total": {"$gt": 1000}}) \
    .build()

# 3. 创建 Outbox 处理器
processor = create_outbox_processor(
    session=session,
    message_bus=smart_bus,  # 使用智能消息总线
    event_registry=event_registry
)

# ❌ 之前的错误方式（不推荐）
# 在 Outbox 层配置复杂路由
routing_config = RoutingConfigBuilder().add_target(...).build()
record = OutboxRecord.from_domain_event(event, routing_config)
```

## 🎯 **迁移步骤**

### **1. 更新导入**
```python
# 查找并替换
- SimpleOutboxProcessor → OutboxProcessor
- create_simple_outbox_processor → create_outbox_processor
```

### **2. 移除 Outbox 层的路由配置**
```python
# ❌ 移除这种用法
routing_config = RoutingConfigBuilder()...
record = OutboxRecord.from_domain_event(event, routing_config)

# ✅ 改为简单存储
record = OutboxRecord.from_domain_event(event)
```

### **3. 在 MessageBus 层配置路由**
```python
# ✅ 正确的配置方式
smart_bus = SmartMessageBus(base_bus)
configure_routing(smart_bus) \
    .for_event("EventType") \
    .route_to("destination", conditions={...}) \
    .build()
```

## 💡 **设计原理**

### **为什么这样重构？**

1. **✅ 符合 DDD 原则**
   - Domain 层：纯领域概念
   - Application 层：业务流程编排
   - Infrastructure 层：技术实现
   - Persistence 层：数据存储

2. **✅ 遵循六边形架构**
   - MessageBus 是端口（Port）
   - 具体消息系统是适配器（Adapter）
   - Outbox 是持久化机制

3. **✅ 单一职责原则**
   - Outbox：事务性存储
   - MessageBus：智能路由
   - Processor：可靠投递

4. **✅ 开闭原则**
   - 轻松扩展新的消息系统
   - 路由逻辑独立演进
   - 不影响存储层

### **架构优势**

| 优势 | 说明 |
|------|------|
| **可测试性** | InProcessMessageBus 便于单元测试 |
| **可扩展性** | 轻松添加 Kafka、RabbitMQ 等适配器 |
| **可维护性** | 职责清晰，修改影响范围小 |
| **性能优化** | 路由逻辑与存储逻辑分离 |

## 🔧 **高级用法**

### **自定义消息总线**
```python
class CustomMessageBus:
    async def publish(self, event: DomainEvent) -> None:
        # 自定义发布逻辑
        pass

# 集成到 Outbox 处理器
processor = create_outbox_processor(
    session=session,
    message_bus=CustomMessageBus(),
    event_registry=registry
)
```

### **路由规则管理**
```python
# 动态添加路由规则
smart_bus.add_routing_rule("NewEventType", {
    "targets": [
        {"destination": "new.service", "conditions": {...}}
    ]
})

# 移除路由规则
smart_bus.remove_routing_rule("OldEventType")
```

## 📋 **检查清单**

- [ ] 更新所有 `SimpleOutboxProcessor` 引用
- [ ] 更新所有 `create_simple_outbox_processor` 引用
- [ ] 移除 Outbox 层的路由配置代码
- [ ] 在 MessageBus 层添加路由配置
- [ ] 更新相关测试代码
- [ ] 更新文档和示例

## 🎉 **总结**

这次重构让 Bento Outbox 模块：

- ✅ **更符合 DDD 原则**：职责清晰分层
- ✅ **更易于测试**：组件独立可测
- ✅ **更好扩展性**：轻松添加新功能
- ✅ **更高性能**：避免不必要的复杂性

现在的架构是真正的 **DDD + 六边形架构最佳实践**！🎊
