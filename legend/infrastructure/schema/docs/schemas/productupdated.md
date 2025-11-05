# ProductUpdated

*产品更新事件*

## 基本信息

- **格式**: AVRO
- **主题**: `persistent://idp/framework/product.updated`
- **版本**: 1

## Schema 定义

```json
{
  "type": "record",
  "name": "ProductUpdated",
  "namespace": "com.idp.events",
  "doc": "产品更新事件",
  "fields": [
    {
      "name": "product_id",
      "type": "string",
      "doc": "产品ID"
    },
    {
      "name": "name",
      "type": "string",
      "doc": "产品名称"
    },
    {
      "name": "description",
      "type": [
        "null",
        "string"
      ],
      "default": null,
      "doc": "产品描述"
    },
    {
      "name": "price",
      "type": "double",
      "doc": "价格"
    },
    {
      "name": "currency",
      "type": "string",
      "doc": "货币"
    },
    {
      "name": "categories",
      "type": {
        "type": "array",
        "items": "string"
      },
      "doc": "分类"
    },
    {
      "name": "attributes",
      "type": {
        "type": "map",
        "values": "string"
      },
      "doc": "属性"
    },
    {
      "name": "in_stock",
      "type": "boolean",
      "doc": "是否有库存"
    },
    {
      "name": "updated_at",
      "type": {
        "type": "long",
        "logicalType": "timestamp-millis"
      },
      "doc": "更新时间"
    }
  ]
}
```

## 使用示例

### 发布事件

```python
from idp.framework.infrastructure.schema import load_schema
from idp.framework.infrastructure.messaging import EventBus

# 获取 Schema 并使用它创建事件
schema = load_schema('ProductUpdated')
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
@event_bus.subscribe('persistent://idp/framework/product.updated')
async def handle_productupdated(data):
    # 处理事件数据
    print(f'收到 ProductUpdated 事件: {data}')
```
