# ProductAdded

*新增产品事件*

## 基本信息

- **格式**: PROTO
- **主题**: `persistent://public/default/product.added`
- **版本**: 1

## Schema 定义

```protobuf
syntax = "proto3";

package events;

import "google/protobuf/timestamp.proto";

// ProductAdded: 新增产品事件
message ProductAdded {
  string product_id = 1;           // 产品ID
  string name = 2;                 // 产品名称
  string description = 3;          // 产品描述
  double price = 4;                // 价格
  repeated string categories = 5;  // 产品分类
  repeated ProductImage images = 6; // 产品图片
  ProductStatus status = 7;        // 产品状态
  google.protobuf.Timestamp created_at = 8;  // 创建时间
  string created_by = 9;           // 创建人ID
  
  // 产品图片
  message ProductImage {
    string url = 1;                // 图片URL
    string alt = 2;                // 替代文本
    bool is_primary = 3;           // 是否主图
  }
  
  // 产品状态枚举
  enum ProductStatus {
    DRAFT = 0;        // 草稿
    ACTIVE = 1;       // 已上架
    INACTIVE = 2;     // 已下架
    DELETED = 3;      // 已删除
  }
} 
```

## 使用示例

### 发布事件

```python
from idp.framework.infrastructure.schema import load_schema
from idp.framework.infrastructure.messaging import EventBus

# 获取 Schema 并使用它创建事件
schema = load_schema('ProductAdded')
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
@event_bus.subscribe('persistent://public/default/product.added')
async def handle_productadded(data):
    # 处理事件数据
    print(f'收到 ProductAdded 事件: {data}')
```
