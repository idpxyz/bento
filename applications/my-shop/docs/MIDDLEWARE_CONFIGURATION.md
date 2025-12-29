# my-shop Middleware Configuration

## 概述

my-shop 应用使用 Bento Framework 提供的企业级 middleware 套件，提供完整的可观测性、安全性和性能保护。

## 已启用的 Middleware

### 1. RequestIDMiddleware ✅
**功能**: 为每个请求生成唯一 ID

**配置**:
```python
app.add_middleware(
    RequestIDMiddleware,
    header_name="X-Request-ID",
)
```

**使用方式**:
- 自动为每个请求生成 UUID
- 客户端可提供自己的 Request ID
- 响应中包含 `X-Request-ID` header
- 在代码中通过 `request.state.request_id` 访问

**示例**:
```bash
# 自动生成
curl http://localhost:8000/ping
# Response headers: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000

# 客户端提供
curl -H "X-Request-ID: my-custom-id" http://localhost:8000/ping
# Response headers: X-Request-ID: my-custom-id
```

---

### 2. StructuredLoggingMiddleware ✅
**功能**: 结构化 JSON 日志记录

**配置**:
```python
app.add_middleware(
    StructuredLoggingMiddleware,
    logger_name="my-shop",
    log_request_body=False,  # 生产环境关闭
    log_response_body=False,  # 生产环境关闭
    skip_paths={"/health", "/ping", "/metrics"},
)
```

**日志输出示例**:
```json
{
    "event": "http_response",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "method": "POST",
    "path": "/api/v1/orders/",
    "status_code": 201,
    "duration_ms": 45.2,
    "client_ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
}
```

**特性**:
- 自动过滤敏感 headers (Authorization, Cookie, X-API-Key)
- 跳过健康检查路径
- 根据状态码自动选择日志级别 (>=500: ERROR, >=400: WARNING, <400: INFO)

---

### 3. RateLimitingMiddleware ✅
**功能**: API 限流保护

**配置**:
```python
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000,
    key_func=lambda req: req.client.host if req.client else "unknown",
    skip_paths={"/health", "/ping"},
)
```

**限制**:
- 每分钟 60 个请求
- 每小时 1000 个请求
- 按客户端 IP 限流

**响应 Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1735459200
```

**超出限制响应** (429):
```json
{
    "error": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "limit": 60,
    "remaining": 0,
    "reset": 1735459200
}
```

---

### 4. IdempotencyMiddleware ✅
**功能**: 请求去重，防止重复操作

**配置**:
```python
app.add_middleware(
    IdempotencyMiddleware,
    header_name="x-idempotency-key",
    ttl_seconds=86400,  # 24 hours
    tenant_id="default",
)
```

**使用方式**:
```bash
# 第一次请求
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "x-idempotency-key: order-12345" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-001", "items": [...]}'
# Response: 201 Created

# 重复请求（返回缓存结果）
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "x-idempotency-key: order-12345" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-001", "items": [...]}'
# Response: 201 Created (same result)
# Headers: X-Idempotent-Replay: 1
```

**冲突检测**:
```bash
# 相同 key，不同参数
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "x-idempotency-key: order-12345" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-002", "items": [...]}'
# Response: 409 Conflict
```

---

### 5. CORSMiddleware ✅
**功能**: 跨域资源共享

**配置**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Middleware 执行顺序

**重要**: Middleware 的执行顺序很关键！

```
请求流向 →
1. RequestIDMiddleware       # 生成 request_id
2. StructuredLoggingMiddleware  # 记录请求
3. RateLimitingMiddleware    # 限流检查
4. IdempotencyMiddleware     # 幂等性检查
5. CORSMiddleware            # CORS 处理
6. 业务逻辑处理
← 响应流向
```

**原理**:
- RequestID 最先执行，为后续 middleware 提供 request_id
- Logging 在 RateLimiting 之后，避免记录被限流的请求
- RateLimiting 在业务逻辑前，尽早拒绝过量请求
- Idempotency 在业务逻辑前，但在 RateLimiting 后
- CORS 通常最后

---

## 测试

使用提供的测试脚本验证所有 middleware：

```bash
cd /workspace/bento/applications/my-shop
./test_middleware.sh
```

测试内容：
1. ✅ Request ID 生成和传递
2. ✅ Rate Limiting 限流和 headers
3. ✅ Idempotency 缓存和重放
4. ✅ Idempotency 冲突检测
5. ✅ Structured Logging 输出

---

## 生产环境建议

### 1. 日志配置
```python
# 关闭请求/响应 body 记录
app.add_middleware(
    StructuredLoggingMiddleware,
    log_request_body=False,  # ❌ 生产环境关闭
    log_response_body=False,  # ❌ 生产环境关闭
)
```

### 2. 限流配置
```python
# 根据业务调整限流参数
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=100,  # 根据容量调整
    requests_per_hour=5000,
)
```

### 3. 使用 Redis 存储
```python
# 当前使用内存存储，生产环境建议使用 Redis
# TODO: 实现 Redis 存储后端
```

### 4. 监控告警
- 监控 429 响应数量（限流触发）
- 监控 409 响应数量（幂等性冲突）
- 监控请求延迟（duration_ms）
- 设置告警阈值

---

## 自定义配置

### 按用户限流
```python
def get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    return user.id if user else request.client.host

app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=100,
    key_func=get_user_id,
)
```

### 自定义 Request ID 格式
```python
def custom_id_generator() -> str:
    import datetime
    import secrets
    date = datetime.datetime.now().strftime("%Y%m%d")
    random = secrets.token_hex(4)
    return f"myshop-{date}-{random}"

app.add_middleware(
    RequestIDMiddleware,
    generator=custom_id_generator,
)
```

---

## 故障排查

### Request ID 未出现
- 检查 middleware 是否正确注册
- 检查 middleware 顺序

### 限流不生效
- 检查 skip_paths 配置
- 检查 key_func 是否正确提取 key
- 注意：内存存储在应用重启后会清空

### Idempotency 不工作
- 检查数据库连接
- 检查 idempotency 表是否存在
- 检查 request_hash 是否匹配

### 日志未输出
- 检查日志级别配置
- 检查 skip_paths 配置
- 检查 logger_name 是否正确

---

## 参考

- [Bento Middleware 文档](../../../src/bento/runtime/middleware/README.md)
- [Middleware 设计文档](../../../src/bento/runtime/middleware/MIDDLEWARE_DESIGN.md)
- [测试脚本](../test_middleware.sh)
