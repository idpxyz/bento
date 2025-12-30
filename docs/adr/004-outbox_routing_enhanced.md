# ADR-004: Enhanced Outbox Routing for Maximum Extensibility

## 🎯 **路由扩展性问题分析**

当前简化设计的路由限制：
- ❌ 单个 `routing_key` 字符串难以表达复杂路由规则
- ❌ 无法支持条件路由（基于事件内容）
- ❌ 缺少路由策略版本管理
- ❌ 多目标路由需要字符串解析

## 🚀 **方案1：智能路由配置 (推荐)**

### **数据库设计增强**
```sql
CREATE TABLE outbox_events (
    -- 原有字段保持不变...
    id VARCHAR(26) PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    -- ... 其他字段

    -- 增强路由字段
    routing_config JSONB DEFAULT '{}',      -- 结构化路由配置
    routing_key VARCHAR(100),               -- 保留简单路由（向下兼容）

    -- 新增：路由策略版本
    routing_version SMALLINT DEFAULT 1      -- 支持路由策略演化
);

-- 路由配置索引
CREATE INDEX idx_outbox_routing ON outbox_events
USING GIN (routing_config) WHERE routing_config != '{}';
```

### **智能路由配置结构**
```json
{
  "targets": [
    {
      "destination": "catalog.product.created",
      "conditions": {
        "payload.category": "electronics",
        "payload.price": {"$gt": 1000}
      },
      "transform": {
        "include_fields": ["id", "name", "price"],
        "exclude_fields": ["internal_notes"]
      }
    },
    {
      "destination": "search.index",
      "conditions": {},
      "delay_seconds": 5,
      "retry_policy": "exponential"
    },
    {
      "destination": "analytics.*",
      "conditions": {"payload.trackable": true},
      "sampling_rate": 0.1
    }
  ],
  "fallback": "default.events",
  "strategy": "all_or_nothing"
}
```

### **路由处理器实现**
```python
@dataclass
class RoutingRule:
    """路由规则"""
    destination: str
    conditions: dict = field(default_factory=dict)
    transform: dict = field(default_factory=dict)
    delay_seconds: int = 0
    sampling_rate: float = 1.0
    retry_policy: str = "default"

class SmartRouter:
    """智能事件路由器"""

    def resolve_destinations(self, event: OutboxEvent) -> list[DestinationConfig]:
        """解析事件的目标路由"""
        # 1. 简单路由（向下兼容）
        if not event.routing_config and event.routing_key:
            return [DestinationConfig(event.routing_key)]

        # 2. 智能路由
        routing_config = event.routing_config
        destinations = []

        for rule_data in routing_config.get("targets", []):
            rule = RoutingRule(**rule_data)

            # 条件匹配
            if self._match_conditions(rule.conditions, event):
                # 采样决策
                if self._should_sample(rule.sampling_rate):
                    destinations.append(DestinationConfig(
                        destination=rule.destination,
                        payload=self._transform_payload(event.payload, rule.transform),
                        delay=rule.delay_seconds,
                        retry_policy=rule.retry_policy
                    ))

        # 降级策略
        if not destinations and routing_config.get("fallback"):
            destinations.append(DestinationConfig(routing_config["fallback"]))

        return destinations

    def _match_conditions(self, conditions: dict, event: OutboxEvent) -> bool:
        """条件匹配引擎"""
        if not conditions:
            return True

        for path, expected in conditions.items():
            actual = self._extract_value(event, path)
            if not self._compare_values(actual, expected):
                return False
        return True

    def _extract_value(self, event: OutboxEvent, path: str):
        """路径提取：支持 payload.field.subfield 语法"""
        parts = path.split(".")
        value = event

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value
```

## 🚀 **方案2：插件化路由引擎**

### **路由引擎接口**
```python
from abc import ABC, abstractmethod
from typing import Protocol

class RoutingEngine(Protocol):
    """路由引擎接口"""

    def resolve_routes(self, event: OutboxEvent) -> list[RouteDestination]:
        """解析事件路由"""
        ...

    def supports_version(self, version: int) -> bool:
        """是否支持特定路由版本"""
        ...

class SimpleRoutingEngine:
    """简单路由引擎（默认）"""

    def resolve_routes(self, event: OutboxEvent) -> list[RouteDestination]:
        if event.routing_key:
            return [RouteDestination(event.routing_key)]
        return [RouteDestination("default")]

class ConditionalRoutingEngine:
    """条件路由引擎"""

    def __init__(self):
        self.rule_engine = RuleEngine()

    def resolve_routes(self, event: OutboxEvent) -> list[RouteDestination]:
        return self.rule_engine.evaluate(event.routing_config, event)

class MLRoutingEngine:
    """机器学习路由引擎（未来扩展）"""

    def resolve_routes(self, event: OutboxEvent) -> list[RouteDestination]:
        # 基于历史数据和ML模型的智能路由
        return self.ml_model.predict_routes(event)

# 路由引擎注册中心
class RoutingEngineRegistry:
    """路由引擎注册中心"""

    def __init__(self):
        self.engines = {
            1: SimpleRoutingEngine(),
            2: ConditionalRoutingEngine(),
            3: MLRoutingEngine(),
        }

    def get_engine(self, version: int) -> RoutingEngine:
        return self.engines.get(version, self.engines[1])
```

## 🚀 **方案3：声明式路由DSL**

### **路由DSL语法**
```yaml
# routing_rules.yaml
version: 2
rules:
  - name: "high_value_products"
    when: "topic == 'product.created' AND payload.price > 1000"
    routes:
      - destination: "vip.notifications"
        transform:
          template: "high_value_product.json"
          fields: ["id", "name", "price"]
      - destination: "fraud.detection"
        condition: "payload.category in ['electronics', 'jewelry']"

  - name: "search_indexing"
    when: "topic matches 'product.*' AND payload.visible == true"
    routes:
      - destination: "search.index"
        delay: "5s"
        batch_size: 100

  - name: "analytics_sampling"
    when: "topic matches '*.created'"
    routes:
      - destination: "analytics.events"
        sampling: 0.1  # 10% 采样

  - name: "fallback"
    when: "true"  # 默认规则
    routes:
      - destination: "dead_letter_queue"
```

### **DSL解析器**
```python
class RoutingDSLEngine:
    """DSL路由引擎"""

    def __init__(self, rules_file: str):
        self.rules = self._parse_rules(rules_file)
        self.expression_engine = ExpressionEngine()

    def resolve_routes(self, event: OutboxEvent) -> list[RouteDestination]:
        """基于DSL规则解析路由"""
        matched_destinations = []

        for rule in self.rules:
            if self._evaluate_condition(rule["when"], event):
                for route in rule["routes"]:
                    if self._evaluate_route_condition(route, event):
                        destination = self._build_destination(route, event)
                        matched_destinations.append(destination)

        return matched_destinations

    def _evaluate_condition(self, condition: str, event: OutboxEvent) -> bool:
        """评估条件表达式"""
        context = {
            "topic": event.topic,
            "payload": event.payload,
            "aggregate_type": event.aggregate_type,
            "tenant_id": event.tenant_id
        }
        return self.expression_engine.evaluate(condition, context)
```

## 📊 **方案对比**

| 方案 | 复杂度 | 扩展性 | 性能 | 学习成本 | 推荐场景 |
|------|--------|--------|------|----------|----------|
| **智能路由配置** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **通用推荐** |
| **插件化引擎** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 复杂业务场景 |
| **声明式DSL** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 规则复杂场景 |

## 🎯 **推荐实现策略**

### **阶段1：智能路由配置**
```sql
-- 立即升级数据库
ALTER TABLE outbox_events ADD COLUMN routing_config JSONB DEFAULT '{}';
ALTER TABLE outbox_events ADD COLUMN routing_version SMALLINT DEFAULT 1;
```

### **阶段2：逐步演化**
```python
# 保持向下兼容
class OutboxProcessor:
    def __init__(self):
        self.simple_router = SimpleRouter()      # 处理 routing_key
        self.smart_router = SmartRouter()        # 处理 routing_config

    def process_event(self, event: OutboxEvent):
        # 智能降级
        if event.routing_config:
            destinations = self.smart_router.resolve_destinations(event)
        else:
            destinations = self.simple_router.resolve_destinations(event)

        return self._dispatch_to_destinations(destinations)
```

### **使用示例**
```python
# 简单路由（保持兼容）
event = OutboxEvent(
    topic="product.created",
    routing_key="catalog.product.created"  # 简单场景
)

# 智能路由（高扩展性）
event = OutboxEvent(
    topic="product.created",
    routing_config={
        "targets": [
            {
                "destination": "search.index",
                "conditions": {"payload.visible": True}
            },
            {
                "destination": "recommendations",
                "conditions": {"payload.category": "electronics"},
                "delay_seconds": 300,
                "sampling_rate": 0.2
            }
        ],
        "strategy": "best_effort"
    }
)
```

## ✅ **最终扩展性评价**

采用智能路由配置后：

| 扩展维度 | 优化前 | 优化后 | 提升 |
|----------|--------|--------|------|
| **路由灵活性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | **显著提升** |
| **条件路由** | ❌ | ✅ | **新增能力** |
| **策略版本化** | ❌ | ✅ | **新增能力** |
| **性能影响** | - | ⭐⭐⭐⭐ | **最小影响** |
| **向下兼容** | - | ✅ | **完全兼容** |

**新的扩展性评分：⭐⭐⭐⭐⭐**

这样既保持了原设计的简洁性，又获得了企业级的路由扩展能力！🚀
