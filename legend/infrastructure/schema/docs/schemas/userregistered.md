# UserRegistered

*用户注册事件*

## 基本信息

- **格式**: PROTO
- **主题**: `persistent://public/default/user.registered`
- **版本**: 1

## Schema 定义

```protobuf
syntax = "proto3";

package events;

import "google/protobuf/timestamp.proto";

// UserRegistered: 用户注册事件
message UserRegistered {
  string user_id = 1;              // 用户ID
  string username = 2;             // 用户名
  string email = 3;                // 邮箱
  google.protobuf.Timestamp registered_at = 4;  // 注册时间
  RegistrationType registration_type = 5;       // 注册类型
  map<string, string> metadata = 6;             // 元数据
  
  // 注册类型枚举
  enum RegistrationType {
    STANDARD = 0;    // 标准注册
    SOCIAL = 1;      // 社交媒体注册
    INVITATION = 2;  // 邀请注册
  }
} 
```

## 使用示例

### 发布事件

```python
from idp.framework.infrastructure.schema import load_schema
from idp.framework.infrastructure.messaging import EventBus

# 获取 Schema 并使用它创建事件
schema = load_schema('UserRegistered')
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
@event_bus.subscribe('persistent://public/default/user.registered')
async def handle_userregistered(data):
    # 处理事件数据
    print(f'收到 UserRegistered 事件: {data}')
```
