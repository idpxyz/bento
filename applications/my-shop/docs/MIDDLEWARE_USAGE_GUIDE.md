# my-shop API Middleware 使用指南

## 概述

my-shop 已集成完整的 Bento Framework middleware 栈。本文档说明各个 API 端点应该如何使用这些 middleware 的特性。

## 已启用的 Middleware

### 1. RequestIDMiddleware ✅
**自动应用于所有请求**

**特性**:
- 每个请求自动生成唯一 ID
- 响应中包含 `X-Request-ID` header
- 可在日志中追踪请求

**API 使用建议**:
```python
from fastapi import Request

@router.post("/orders/")
async def create_order(request: Request, ...):
    # 获取 request_id 用于日志
    request_id = request.state.request_id
    logger.info(f"Creating order, request_id={request_id}")

    # 业务逻辑...
    return result
```

**客户端使用**:
```bash
# 客户端可提供自己的 request_id
curl -H "X-Request-ID: my-custom-id-123" http://localhost:8000/api/v1/orders/

# 或让服务端自动生成
curl http://localhost:8000/api/v1/orders/
# Response headers: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

### 2. StructuredLoggingMiddleware ✅
**自动记录所有请求/响应**

**特性**:
- 自动记录 HTTP 请求元数据
- JSON 格式日志
- 自动过滤敏感 headers

**无需代码修改**，所有请求自动记录：
```json
{
    "event": "http_response",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "method": "POST",
    "path": "/api/v1/orders/",
    "status_code": 201,
    "duration_ms": 45.2,
    "client_ip": "192.168.1.1"
}
```

**跳过的路径**:
- `/health`
- `/ping`
- `/metrics`

---

### 3. RateLimitingMiddleware ✅
**自动限流保护**

**当前配置**:
- 每分钟 60 个请求
- 每小时 1000 个请求
- 按客户端 IP 限流

**响应 Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1735459200
```

**超出限制**:
```json
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "limit": 60,
    "remaining": 0,
    "reset": 1735459200
}
```

**API 使用建议**:
- 无需代码修改
- 客户端应检查 `X-RateLimit-*` headers
- 客户端应处理 429 响应

**跳过的路径**:
- `/health`
- `/ping`

---

### 4. IdempotencyMiddleware ✅
**防止重复操作**

**适用场景**:
- ✅ **订单创建** (POST /api/v1/orders/)
- ✅ **支付处理** (POST /api/v1/orders/{id}/pay)
- ✅ **发货操作** (POST /api/v1/orders/{id}/ship)
- ✅ **分类创建** (POST /api/v1/categories/)
- ✅ **产品创建** (POST /api/v1/products/)

**不适用场景**:
- ❌ 查询操作 (GET)
- ❌ 健康检查 (GET /health)
- ❌ 列表操作 (GET /api/v1/orders/)

**客户端使用**:
```bash
# 订单创建（幂等）
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "x-idempotency-key: order-20251229-001" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-001",
    "items": [...]
  }'

# 重复请求返回相同结果
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "x-idempotency-key: order-20251229-001" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-001",
    "items": [...]
  }'
# Response: 201 Created (same order)
# Headers: X-Idempotent-Replay: 1
```

**Idempotency Key 生成建议**:
```javascript
// 前端生成 idempotency key
function generateIdempotencyKey(operation, entityId) {
    const timestamp = new Date().toISOString().split('T')[0];
    const random = Math.random().toString(36).substring(7);
    return `${operation}-${timestamp}-${entityId}-${random}`;
}

// 示例
const key = generateIdempotencyKey('order', 'cust-001');
// "order-2025-12-29-cust-001-a3f9d2"
```

---

### 5. TenantMiddleware 💤
**多租户支持（可选，未启用）**

**当前状态**: 未启用

**如需启用**: 参考 `docs/MULTI_TENANCY_ANALYSIS.md`

---

## API 端点 Middleware 应用矩阵

| API 端点 | RequestID | Logging | RateLimiting | Idempotency | 说明 |
|---------|-----------|---------|--------------|-------------|------|
| **订单 API** |
| POST /api/v1/orders/ | ✅ | ✅ | ✅ | ✅ 推荐 | 创建订单，强烈建议使用幂等性 |
| GET /api/v1/orders/ | ✅ | ✅ | ✅ | ❌ | 查询订单列表 |
| GET /api/v1/orders/{id} | ✅ | ✅ | ✅ | ❌ | 查询单个订单 |
| POST /api/v1/orders/{id}/pay | ✅ | ✅ | ✅ | ✅ 推荐 | 支付订单，强烈建议使用幂等性 |
| POST /api/v1/orders/{id}/ship | ✅ | ✅ | ✅ | ✅ 推荐 | 发货，强烈建议使用幂等性 |
| **产品 API** |
| POST /api/v1/products/ | ✅ | ✅ | ✅ | ✅ 可选 | 创建产品 |
| GET /api/v1/products/ | ✅ | ✅ | ✅ | ❌ | 查询产品列表 |
| GET /api/v1/products/{id} | ✅ | ✅ | ✅ | ❌ | 查询单个产品 |
| PUT /api/v1/products/{id} | ✅ | ✅ | ✅ | ✅ 可选 | 更新产品 |
| **分类 API** |
| POST /api/v1/categories/ | ✅ | ✅ | ✅ | ✅ 可选 | 创建分类 |
| GET /api/v1/categories/ | ✅ | ✅ | ✅ | ❌ | 查询分类列表 |
| GET /api/v1/categories/{id} | ✅ | ✅ | ✅ | ❌ | 查询单个分类 |
| **健康检查** |
| GET /health | ✅ | ❌ 跳过 | ❌ 跳过 | ❌ | 健康检查 |
| GET /ping | ✅ | ❌ 跳过 | ❌ 跳过 | ❌ | 心跳检查 |

---

## 客户端集成指南

### 1. 基础请求（所有 API）

```javascript
// 基础请求配置
async function apiRequest(method, url, data = null) {
    const headers = {
        'Content-Type': 'application/json',
    };

    const options = {
        method,
        headers,
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);

    // 获取 request_id 用于日志和支持
    const requestId = response.headers.get('X-Request-ID');
    console.log(`Request ID: ${requestId}`);

    // 检查 rate limit
    const rateLimit = response.headers.get('X-RateLimit-Remaining');
    if (rateLimit && parseInt(rateLimit) < 10) {
        console.warn(`Rate limit warning: ${rateLimit} requests remaining`);
    }

    return response;
}
```

### 2. 幂等请求（订单、支付等）

```javascript
// 幂等请求配置
async function idempotentRequest(method, url, data, idempotencyKey) {
    const headers = {
        'Content-Type': 'application/json',
        'x-idempotency-key': idempotencyKey,
    };

    const response = await fetch(url, {
        method,
        headers,
        body: JSON.stringify(data),
    });

    // 检查是否是重放响应
    const isReplay = response.headers.get('X-Idempotent-Replay');
    if (isReplay === '1') {
        console.log('Received cached response (idempotent replay)');
    }

    return response;
}

// 使用示例：创建订单
async function createOrder(orderData) {
    const idempotencyKey = `order-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    try {
        const response = await idempotentRequest(
            'POST',
            '/api/v1/orders/',
            orderData,
            idempotencyKey
        );

        if (response.ok) {
            return await response.json();
        } else if (response.status === 409) {
            // Idempotency conflict
            const error = await response.json();
            console.error('Idempotency conflict:', error);
            throw new Error('Request parameters changed for same idempotency key');
        }
    } catch (error) {
        console.error('Order creation failed:', error);
        throw error;
    }
}
```

### 3. 处理 Rate Limiting

```javascript
// Rate limiting 处理
async function requestWithRetry(method, url, data, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        const response = await apiRequest(method, url, data);

        if (response.status === 429) {
            // Rate limit exceeded
            const retryAfter = response.headers.get('Retry-After');
            const waitTime = retryAfter ? parseInt(retryAfter) * 1000 : 60000;

            console.warn(`Rate limited. Retrying after ${waitTime}ms...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
            continue;
        }

        return response;
    }

    throw new Error('Max retries exceeded');
}
```

### 4. 完整示例：创建订单

```javascript
// 完整的订单创建流程
async function placeOrder(customerId, items) {
    // 1. 生成 idempotency key
    const idempotencyKey = `order-${customerId}-${Date.now()}`;

    // 2. 准备订单数据
    const orderData = {
        customer_id: customerId,
        items: items,
    };

    // 3. 发送请求
    try {
        const response = await fetch('/api/v1/orders/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-idempotency-key': idempotencyKey,
            },
            body: JSON.stringify(orderData),
        });

        // 4. 处理响应
        if (response.ok) {
            const order = await response.json();
            const requestId = response.headers.get('X-Request-ID');
            const isReplay = response.headers.get('X-Idempotent-Replay');

            console.log('Order created:', order);
            console.log('Request ID:', requestId);

            if (isReplay === '1') {
                console.log('This is a duplicate request, returning cached order');
            }

            return order;
        } else if (response.status === 429) {
            // Rate limited
            const retryAfter = response.headers.get('Retry-After');
            throw new Error(`Rate limited. Retry after ${retryAfter} seconds`);
        } else if (response.status === 409) {
            // Idempotency conflict
            throw new Error('Idempotency conflict: same key with different parameters');
        } else {
            const error = await response.json();
            throw new Error(error.message);
        }
    } catch (error) {
        console.error('Failed to create order:', error);
        throw error;
    }
}
```

---

## 最佳实践

### 1. Request ID 使用

**在日志中使用**:
```python
@router.post("/orders/")
async def create_order(request: Request, command: CreateOrderCommand):
    request_id = request.state.request_id
    logger.info(f"[{request_id}] Creating order for customer {command.customer_id}")

    try:
        order = await handler.execute(command)
        logger.info(f"[{request_id}] Order created: {order.id}")
        return order
    except Exception as e:
        logger.error(f"[{request_id}] Order creation failed: {e}")
        raise
```

**在错误响应中返回**:
```python
@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, 'request_id', 'unknown')
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "request_id": request_id,  # 返回给客户端用于支持
        }
    )
```

### 2. Idempotency Key 策略

**推荐格式**:
```
{operation}-{date}-{entity_id}-{random}
```

**示例**:
- 订单创建: `order-20251229-cust001-a3f9d2`
- 支付: `payment-20251229-order123-b7e4c1`
- 发货: `shipment-20251229-order123-d2f8a9`

**存储建议**:
- 客户端应存储 idempotency key
- 重试时使用相同的 key
- 24 小时后可重用（TTL）

### 3. Rate Limiting 处理

**客户端策略**:
1. 检查 `X-RateLimit-Remaining` header
2. 当剩余次数 < 10 时，减慢请求速度
3. 收到 429 时，等待 `Retry-After` 秒后重试
4. 实现指数退避策略

**服务端调整**:
```python
# 根据业务需求调整限流参数
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=100,  # 提高限制
    requests_per_hour=5000,
)
```

---

## 监控和告警

### 关键指标

1. **Request ID 覆盖率**
   - 所有请求应有 request_id
   - 监控缺失 request_id 的请求

2. **Idempotency 使用率**
   - 监控关键操作的幂等性使用率
   - 目标：订单创建 > 90%

3. **Rate Limiting 触发率**
   - 监控 429 响应数量
   - 设置告警阈值

4. **Idempotency 冲突率**
   - 监控 409 响应数量
   - 可能表示客户端问题

### 日志查询示例

```bash
# 查询特定 request_id 的所有日志
grep "550e8400-e29b-41d4-a716-446655440000" /var/log/my-shop.log

# 查询 rate limiting 事件
grep "RATE_LIMIT_EXCEEDED" /var/log/my-shop.log

# 查询 idempotency 重放
grep "X-Idempotent-Replay" /var/log/my-shop.log
```

---

## 故障排查

### 问题 1: Request ID 未出现

**症状**: 响应中没有 `X-Request-ID` header

**排查**:
1. 检查 RequestIDMiddleware 是否注册
2. 检查 middleware 顺序
3. 查看启动日志

### 问题 2: Idempotency 不工作

**症状**: 重复请求创建了多个订单

**排查**:
1. 检查客户端是否发送 `x-idempotency-key` header
2. 检查数据库 `idempotency` 表
3. 检查 IdempotencyMiddleware 配置

### 问题 3: 频繁触发 Rate Limiting

**症状**: 大量 429 响应

**排查**:
1. 检查客户端请求频率
2. 考虑提高限流阈值
3. 检查是否有恶意请求

---

## 参考

- [Middleware 配置文档](../runtime/bootstrap_v2.py)
- [Bento Middleware README](../../../src/bento/runtime/middleware/README.md)
- [Multi-Tenancy 分析](./MULTI_TENANCY_ANALYSIS.md)
- [测试脚本](../test_middleware.sh)
