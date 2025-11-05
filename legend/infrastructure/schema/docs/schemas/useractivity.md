# UserActivity

*用户活动事件*

## 基本信息

- **格式**: JSON
- **主题**: `persistent://idp/framework/user.activity`
- **版本**: 1

## Schema 定义

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UserActivity",
  "description": "用户活动事件",
  "type": "object",
  "required": [
    "activity_id",
    "user_id",
    "action",
    "timestamp"
  ],
  "properties": {
    "activity_id": {
      "type": "string",
      "description": "活动ID"
    },
    "user_id": {
      "type": "string",
      "description": "用户ID"
    },
    "session_id": {
      "type": "string",
      "description": "会话ID"
    },
    "action": {
      "type": "string",
      "enum": [
        "login",
        "logout",
        "view",
        "click",
        "search",
        "purchase"
      ],
      "description": "活动类型"
    },
    "resource": {
      "type": "object",
      "description": "资源信息",
      "properties": {
        "type": {
          "type": "string",
          "description": "资源类型"
        },
        "id": {
          "type": "string",
          "description": "资源ID"
        },
        "name": {
          "type": "string",
          "description": "资源名称"
        },
        "url": {
          "type": "string",
          "format": "uri",
          "description": "资源URL"
        }
      }
    },
    "device": {
      "type": "object",
      "description": "设备信息",
      "properties": {
        "type": {
          "type": "string",
          "description": "设备类型"
        },
        "os": {
          "type": "string",
          "description": "操作系统"
        },
        "browser": {
          "type": "string",
          "description": "浏览器"
        },
        "ip": {
          "type": "string",
          "format": "ipv4",
          "description": "IP地址"
        }
      }
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "时间戳"
    },
    "metadata": {
      "type": "object",
      "description": "附加元数据",
      "additionalProperties": true
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
schema = load_schema('UserActivity')
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
@event_bus.subscribe('persistent://idp/framework/user.activity')
async def handle_useractivity(data):
    # 处理事件数据
    print(f'收到 UserActivity 事件: {data}')
```
