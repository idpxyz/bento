# OrderCreated

*订单创建事件*

## 基本信息

- **格式**: PROTO
- **主题**: `persistent://idp/framework/order.created`
- **版本**: 1

## Schema 定义

```protobuf
syntax = "proto3";

package events;

import "google/protobuf/timestamp.proto";

// 订单创建事件
message OrderCreated {
    string order_id = 1;                        // 订单ID
    string customer_id = 2;                     // 客户ID
    repeated OrderItem items = 3;               // 订单项目
    double total_amount = 4;                    // 总金额
    string currency = 5;                        // 货币
    string status = 6;                          // 订单状态
    google.protobuf.Timestamp created_at = 7;   // 创建时间
}

// 订单项目
message OrderItem {
    string product_id = 1;                      // 产品ID
    string product_name = 2;                    // 产品名称
    int32 quantity = 3;                         // 数量
    double unit_price = 4;                      // 单价
    double subtotal = 5;                        // 小计
} 
```

## 使用示例

### 发布事件

```python
from idp.framework.infrastructure.schema import load_schema
from idp.framework.infrastructure.messaging import EventBus

# 获取 Schema 并使用它创建事件
schema = load_schema('OrderCreated')
topic = schema.get('topic')

# 创建事件数据
event_data = {
    # 填充事件数据
}

# 发布事件
await event_bus.publish(topic, event_data)
```

### 订阅事件

```python
from idp.framework.infrastructure.messaging import EventBus

# 订阅事件
@event_bus.subscribe('persistent://idp/framework/order.created')
async def handle_ordercreated(data):
    # 处理事件数据
    print(f'收到 OrderCreated 事件: {data}')
```
