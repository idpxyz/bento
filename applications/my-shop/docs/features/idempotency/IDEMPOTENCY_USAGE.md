# Idempotency 使用指南

## 概述

my-shop 使用 Bento Framework 的 `IdempotencyMiddleware` 来防止重复请求。

## ⚠️ 重要：idempotency_key 在 HTTP Header 中

**idempotency_key 必须在 HTTP Header 中传递，而不是在 Request Body 中**。

### 正确的使用方式 ✅

```bash
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: order-20251229-001" \
  -d '{
    "customer_id": "cust-001",
    "items": [...]
  }'
```

### 错误的使用方式 ❌

```bash
# ❌ 错误：idempotency_key 在 Body 中
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-001",
    "items": [...],
    "idempotency_key": "order-20251229-001"  # ❌ 不会被 middleware 识别
  }'
```

## 工作原理

### 1. Middleware 层（自动处理）

`IdempotencyMiddleware` 在请求到达应用层之前：
1. 从 HTTP Header 中读取 `X-Idempotency-Key`
2. 计算请求体的哈希值
3. 检查数据库中是否有相同 key 的请求
4. 如果存在且已完成，返回缓存的响应
5. 如果不存在，继续处理请求

### 2. 应用层（可选）

API 中的 `idempotency_key` 字段是**可选的**，用于：
- 文档目的
- 应用层的额外验证（如果需要）
- 与其他系统的兼容性

## 配置

### Middleware 配置

在 `bootstrap_v2.py` 中：

```python
app.add_middleware(
    IdempotencyMiddleware,
    header_name="X-Idempotency-Key",  # Header 名称
    ttl_seconds=86400,                 # 24 小时缓存
    tenant_id="default",               # 租户 ID
)
```

### 参数说明

- **header_name**: HTTP Header 名称（默认：`X-Idempotency-Key`）
- **ttl_seconds**: 缓存过期时间（默认：86400 秒 = 24 小时）
- **tenant_id**: 租户 ID（用于多租户隔离）

## 使用场景

### 1. 订单创建（强烈推荐）

```bash
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: order-cust001-20251229-001" \
  -d '{
    "customer_id": "cust-001",
    "items": [
      {
        "product_id": "prod-123",
        "product_name": "iPhone 15",
        "quantity": 1,
        "unit_price": 999.99
      }
    ]
  }'
```

**响应（第一次）**:
```json
{
  "id": "order-123",
  "customer_id": "cust-001",
  "status": "pending",
  "total": 999.99
}
```

**响应（第二次，相同 key）**:
```json
{
  "id": "order-123",
  "customer_id": "cust-001",
  "status": "pending",
  "total": 999.99
}
```

### 2. 支付操作（强烈推荐）

```bash
curl -X POST http://localhost:8000/api/v1/orders/order-123/pay \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: payment-order123-20251229-001" \
  -d '{}'
```

### 3. 发货操作（强烈推荐）

```bash
curl -X POST http://localhost:8000/api/v1/orders/order-123/ship \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: shipment-order123-20251229-001" \
  -d '{
    "tracking_number": "SF1234567890"
  }'
```

## idempotency_key 生成策略

### 推荐格式

```
{operation}-{date}-{entity_id}-{random}
```

### 示例

```javascript
function generateIdempotencyKey(operation, entityId) {
  const date = new Date().toISOString().split('T')[0];
  const random = Math.random().toString(36).substring(7);
  return `${operation}-${date}-${entityId}-${random}`;
}

// 使用
const key = generateIdempotencyKey('order', 'cust-001');
// 结果: "order-2025-12-29-cust-001-a3f9d2"
```

### 最佳实践

1. **使用时间戳**：包含日期，便于追踪
2. **包含实体 ID**：便于识别操作对象
3. **添加随机值**：防止碰撞
4. **保存 key**：客户端应保存 key，用于重试

## 重试逻辑

### 客户端重试示例

```javascript
async function createOrderWithRetry(orderData, maxRetries = 3) {
  const idempotencyKey = generateIdempotencyKey('order', orderData.customer_id);

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:8000/api/v1/orders/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Idempotency-Key': idempotencyKey,  // ✅ 在 Header 中
        },
        body: JSON.stringify(orderData),
      });

      if (response.ok) {
        return await response.json();
      }

      // 重试逻辑
      if (response.status === 429 || response.status >= 500) {
        const waitTime = Math.pow(2, i) * 1000; // 指数退避
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }

      throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      if (i === maxRetries - 1) throw error;

      const waitTime = Math.pow(2, i) * 1000;
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }
}
```

## 常见问题

### Q: 为什么我的重复请求没有返回缓存的响应？

**A**: 检查以下几点：
1. ✅ idempotency_key 在 **HTTP Header** 中，而不是 Body 中
2. ✅ Header 名称是 `X-Idempotency-Key`（小写）
3. ✅ 两次请求的 idempotency_key 完全相同
4. ✅ 缓存没有过期（默认 24 小时）

### Q: 如果请求参数不同但 idempotency_key 相同会怎样？

**A**: IdempotencyMiddleware 会检测到参数变化：
- 计算请求体的哈希值
- 如果哈希值不同，返回 409 Conflict 错误
- 防止参数篡改

### Q: idempotency_key 可以重复使用吗？

**A**: 可以，但要注意：
- 24 小时内（默认 TTL）：返回缓存的响应
- 24 小时后：可以重新使用，会创建新的记录

### Q: 如何为不同的操作生成 key？

**A**: 使用不同的前缀：
```
order-{date}-{id}-{random}      # 订单创建
payment-{date}-{id}-{random}    # 支付
shipment-{date}-{id}-{random}   # 发货
```

## 监控和调试

### 查看缓存的请求

```bash
# 查询数据库中的幂等性记录
SELECT * FROM idempotency_records
WHERE idempotency_key = 'order-2025-12-29-cust-001-a3f9d2';
```

### 日志中的 request_id

所有请求都包含 `X-Request-ID` header，可用于追踪：

```bash
# 查看特定请求的日志
grep "550e8400-e29b-41d4-a716-446655440000" /var/log/my-shop.log
```

## 总结

| 方面 | 说明 |
|------|------|
| **传递方式** | HTTP Header: `X-Idempotency-Key` |
| **缓存时间** | 24 小时（可配置） |
| **适用操作** | POST, PUT, PATCH, DELETE |
| **冲突处理** | 参数不同返回 409 |
| **多租户** | 自动隔离（基于 tenant_id） |

**记住：idempotency_key 必须在 HTTP Header 中！** 🔑
