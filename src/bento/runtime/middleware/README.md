# Bento Framework Middleware

企业级 FastAPI middleware 组件集合，提供可观测性、安全性和性能优化。

## 可用的 Middleware

### 1. IdempotencyMiddleware
**功能**: 请求去重，防止重复操作

```python
from bento.runtime.middleware import IdempotencyMiddleware

app.add_middleware(
    IdempotencyMiddleware,
    header_name="x-idempotency-key",
    ttl_seconds=86400,  # 24 hours
    tenant_id="default",
)
```

**使用场景**:
- 订单创建
- 支付处理
- 库存操作
- 任何需要幂等性的关键业务操作

**客户端使用**:
```bash
curl -X POST http://api.example.com/orders \
  -H "x-idempotency-key: order-12345" \
  -H "Content-Type: application/json" \
  -d '{"items": [...]}'
```

---

### 2. RequestIDMiddleware
**功能**: 为每个请求生成唯一 ID，用于分布式追踪

```python
from bento.runtime.middleware import RequestIDMiddleware

app.add_middleware(
    RequestIDMiddleware,
    header_name="X-Request-ID",
)
```

**使用场景**:
- 日志关联
- 分布式追踪
- 问题排查
- 客户支持

**在应用中访问**:
```python
@app.get("/items")
async def get_items(request: Request):
    request_id = request.state.request_id
    logger.info(f"Processing request {request_id}")
    return {"items": [...]}
```

---

### 3. StructuredLoggingMiddleware
**功能**: 结构化日志记录，记录请求/响应元数据

```python
from bento.runtime.middleware import StructuredLoggingMiddleware

app.add_middleware(
    StructuredLoggingMiddleware,
    logger_name="api",
    log_request_body=False,  # 生产环境建议关闭
    log_response_body=False,
)
```

**日志输出示例**:
```json
{
    "event": "http_response",
    "request_id": "abc-123",
    "method": "POST",
    "path": "/api/v1/orders",
    "status_code": 201,
    "duration_ms": 45.2,
    "client_ip": "192.168.1.1"
}
```

**使用场景**:
- 性能监控
- 安全审计
- 问题排查
- 合规要求

---

### 4. RateLimitingMiddleware
**功能**: API 限流，防止滥用和 DDoS 攻击

```python
from bento.runtime.middleware import RateLimitingMiddleware

# 按 IP 限流
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000,
    key_func=lambda req: req.client.host,
)

# 按用户限流
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=100,
    key_func=lambda req: req.state.user.id,
)

# 按 API Key 限流
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=1000,
    key_func=lambda req: req.headers.get("X-API-Key"),
)
```

**响应 Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1735459200
```

**限流超出响应**:
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

### 5. TenantMiddleware
**功能**: 多租户上下文管理（从 multitenancy 模块 re-export）

```python
from bento.runtime.middleware import TenantMiddleware, TenantContext
from bento.multitenancy import HeaderTenantResolver

# 添加租户 middleware
TenantMiddleware(
    app,
    resolver=HeaderTenantResolver(header_name="X-Tenant-ID"),
    require_tenant=False,
    exclude_paths=["/health", "/ping", "/docs"],
)
```

**租户识别策略**:
```python
from bento.multitenancy import (
    HeaderTenantResolver,      # 从 HTTP header 提取
    TokenTenantResolver,        # 从 JWT token 提取
    SubdomainTenantResolver,    # 从子域名提取
    CompositeTenantResolver,    # 组合多种策略
)

# 从 header 提取
resolver = HeaderTenantResolver(header_name="X-Tenant-ID")

# 从 JWT token 提取
resolver = TokenTenantResolver(claim_name="tenant_id")

# 从子域名提取
resolver = SubdomainTenantResolver()

# 组合策略（优先级顺序）
resolver = CompositeTenantResolver([
    TokenTenantResolver(),
    HeaderTenantResolver(),
])
```

**在业务代码中使用**:
```python
from bento.runtime.middleware import TenantContext

@app.get("/orders")
async def get_orders():
    tenant_id = TenantContext.get()  # 获取当前租户（可能为 None）
    tenant_id = TenantContext.require()  # 必须存在，否则抛异常

    # 自动按租户过滤数据
    orders = await order_repo.find_all()
    return orders
```

**使用场景**:
- SaaS 多租户应用
- 白标解决方案
- 企业多部门部署
- 数据隔离需求

**注意**:
- 需要在数据模型中添加 `tenant_id` 字段
- 使用 `TenantFilterMixin` 自动过滤查询
- 参考 `/applications/my-shop/docs/MULTI_TENANCY_ANALYSIS.md`

---

## 完整配置示例

### 推荐的 Middleware 顺序

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bento.runtime.middleware import (
    RequestIDMiddleware,
    StructuredLoggingMiddleware,
    TenantMiddleware,
    RateLimitingMiddleware,
    IdempotencyMiddleware,
    TenantContext,
)
from bento.multitenancy import HeaderTenantResolver

app = FastAPI()

# 1. Request ID (最先执行，为后续 middleware 提供 request_id)
app.add_middleware(
    RequestIDMiddleware,
    header_name="X-Request-ID",
)

# 2. Structured Logging (记录所有请求)
app.add_middleware(
    StructuredLoggingMiddleware,
    logger_name="api",
    log_request_body=False,
    log_response_body=False,
)

# 3. Tenant Context (多租户识别，可选)
TenantMiddleware(
    app,
    resolver=HeaderTenantResolver(),
    require_tenant=False,
    exclude_paths=["/health", "/ping"],
)

# 3. Rate Limiting (在业务逻辑前限流)
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=60,
    key_func=lambda req: req.client.host,
)

# 4. Idempotency (业务逻辑相关)
app.add_middleware(
    IdempotencyMiddleware,
    header_name="x-idempotency-key",
    ttl_seconds=86400,
)

# 5. CORS (FastAPI 内置)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### my-shop 应用示例

```python
# applications/my-shop/runtime/bootstrap_v2.py
from bento.runtime.middleware import (
    RequestIDMiddleware,
    StructuredLoggingMiddleware,
    RateLimitingMiddleware,
    IdempotencyMiddleware,
)

def create_app() -> FastAPI:
    app = runtime.create_fastapi_app(...)

    # Request tracking
    app.add_middleware(RequestIDMiddleware)

    # Structured logging
    app.add_middleware(
        StructuredLoggingMiddleware,
        logger_name="my-shop",
    )

    # Rate limiting (60 req/min per IP)
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=60,
    )

    # Idempotency for order creation
    app.add_middleware(
        IdempotencyMiddleware,
        ttl_seconds=86400,
    )

    # CORS
    app.add_middleware(CORSMiddleware, ...)

    return app
```

---

## 最佳实践

### 1. Middleware 顺序很重要
- **RequestID** 应该最先，为其他 middleware 提供 request_id
- **Logging** 应该在 RateLimiting 之后，避免记录被限流的请求
- **RateLimiting** 应该在业务逻辑前，尽早拒绝过量请求
- **Idempotency** 应该在业务逻辑前，但在 RateLimiting 后
- **CORS** 通常最后

### 2. 生产环境配置
```python
# 不要在生产环境记录请求/响应 body
app.add_middleware(
    StructuredLoggingMiddleware,
    log_request_body=False,  # ❌ 生产环境关闭
    log_response_body=False,  # ❌ 生产环境关闭
)

# 使用合理的限流配置
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=100,  # 根据业务调整
    requests_per_hour=5000,
)
```

### 3. 敏感数据保护
```python
# StructuredLoggingMiddleware 自动过滤敏感 headers
# 默认过滤: Authorization, Cookie, X-API-Key 等
app.add_middleware(
    StructuredLoggingMiddleware,
    sensitive_headers={
        "authorization",
        "cookie",
        "x-api-key",
        "x-custom-secret",  # 添加自定义敏感 header
    },
)
```

### 4. 性能优化
```python
# 跳过健康检查等路径的日志和限流
app.add_middleware(
    StructuredLoggingMiddleware,
    skip_paths={"/health", "/ping", "/metrics"},
)

app.add_middleware(
    RateLimitingMiddleware,
    skip_paths={"/health", "/ping"},
)
```

---

## 扩展和自定义

### 自定义 Request ID 生成器
```python
def custom_id_generator() -> str:
    # 使用自定义格式，如: myapp-20251229-abc123
    import datetime
    import secrets
    date = datetime.datetime.now().strftime("%Y%m%d")
    random = secrets.token_hex(4)
    return f"myapp-{date}-{random}"

app.add_middleware(
    RequestIDMiddleware,
    generator=custom_id_generator,
)
```

### 自定义限流 Key
```python
# 按用户 ID 限流
def get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    return user.id if user else request.client.host

app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=100,
    key_func=get_user_id,
)
```

---

## 监控和告警

### 集成 Prometheus
```python
from prometheus_client import Counter, Histogram

# 在 StructuredLoggingMiddleware 中添加指标
request_count = Counter("http_requests_total", "Total HTTP requests")
request_duration = Histogram("http_request_duration_seconds", "HTTP request duration")
```

### 集成 Sentry
```python
import sentry_sdk

# StructuredLoggingMiddleware 会自动记录异常
# 可以在日志中添加 request_id 用于关联
```

---

## 参考

- [FastAPI Middleware](https://fastapi.tiangolo.com/advanced/middleware/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [Stripe API Design](https://stripe.com/docs/api)
- [AWS API Best Practices](https://docs.aws.amazon.com/apigateway/)
