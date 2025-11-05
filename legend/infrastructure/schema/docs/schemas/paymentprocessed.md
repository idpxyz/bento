# PaymentProcessed

*支付处理完成事件*

## 基本信息

- **格式**: JSON
- **主题**: `persistent://public/default/payment.processed`
- **版本**: 1

## Schema 定义

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PaymentProcessed",
  "description": "支付处理完成事件",
  "type": "object",
  "required": [
    "payment_id",
    "order_id",
    "amount",
    "status",
    "payment_method",
    "processed_at"
  ],
  "properties": {
    "payment_id": {
      "type": "string",
      "description": "支付ID"
    },
    "order_id": {
      "type": "string",
      "description": "关联的订单ID"
    },
    "transaction_id": {
      "type": "string",
      "description": "支付网关交易ID"
    },
    "amount": {
      "type": "number",
      "description": "支付金额"
    },
    "currency": {
      "type": "string",
      "default": "CNY",
      "description": "货币类型"
    },
    "status": {
      "type": "string",
      "enum": [
        "SUCCEEDED",
        "FAILED",
        "PENDING",
        "REFUNDED"
      ],
      "description": "支付状态"
    },
    "payment_method": {
      "type": "object",
      "required": [
        "type"
      ],
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "CREDIT_CARD",
            "DEBIT_CARD",
            "ALIPAY",
            "WECHAT",
            "BANK_TRANSFER"
          ],
          "description": "支付方式类型"
        },
        "last4": {
          "type": "string",
          "description": "卡号末四位（如适用）"
        },
        "expiry_date": {
          "type": "string",
          "description": "过期日期（如适用）"
        }
      },
      "description": "支付方式详情"
    },
    "processed_at": {
      "type": "string",
      "format": "date-time",
      "description": "处理时间"
    },
    "error_code": {
      "type": "string",
      "description": "错误代码（如果支付失败）"
    },
    "error_message": {
      "type": "string",
      "description": "错误消息（如果支付失败）"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      },
      "description": "元数据"
    }
  }
}
```

## 使用示例

### 发布事件

```python
from idp.framework.infrastructure.schema import load_schema
from idp.framework.infrastructure.messaging import EventBus

# 获取 Schema 并使用它创建事件
schema = load_schema('PaymentProcessed')
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
@event_bus.subscribe('persistent://public/default/payment.processed')
async def handle_paymentprocessed(data):
    # 处理事件数据
    print(f'收到 PaymentProcessed 事件: {data}')
```
