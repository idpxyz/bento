# Bento Framework Middleware Architecture

## 已实现的 Middleware

### 1. IdempotencyMiddleware ✅
- **功能**: 请求去重，防止重复操作
- **优先级**: 高（已实现）
- **使用场景**: 订单创建、支付、库存操作等关键业务

## 推荐实现的 Middleware

### 2. RequestIDMiddleware 🔥 (高优先级)
**功能**: 为每个请求生成唯一 ID，用于日志追踪和分布式追踪

**业界实践**:
- AWS: X-Amzn-RequestId
- Google Cloud: X-Cloud-Trace-Context
- Stripe: Request-Id

**实现要点**:
```python
class RequestIDMiddleware:
    """Generate unique request ID for tracing."""

    - 生成 UUID 或使用客户端提供的 ID
    - 注入到 request.state.request_id
    - 添加到响应 header: X-Request-ID
    - 集成到日志系统
```

**优势**:
- 端到端请求追踪
- 问题排查和调试
- 分布式系统关联
- 客户支持（提供 request_id）

---

### 3. StructuredLoggingMiddleware 🔥 (高优先级)
**功能**: 结构化日志记录，记录请求/响应元数据

**业界实践**:
- 所有主流云服务都有
- ELK Stack、Datadog、Splunk 等日志平台

**实现要点**:
```python
class StructuredLoggingMiddleware:
    """Structured logging for requests."""

    - 记录请求: method, path, headers, body
    - 记录响应: status_code, duration, size
    - 结构化格式: JSON
    - 可配置敏感字段过滤
```

**优势**:
- 可观测性
- 性能监控
- 安全审计
- 问题排查

---

### 4. RateLimitingMiddleware 🔥 (高优先级)
**功能**: 限流，防止 API 滥用和 DDoS 攻击

**业界实践**:
- Stripe: 按用户限流
- GitHub: 按 IP 和用户限流
- AWS: 按 API Key 限流

**实现要点**:
```python
class RateLimitingMiddleware:
    """Rate limiting for API protection."""

    - 支持多种策略: 固定窗口、滑动窗口、令牌桶
    - 支持多维度: IP、用户、API Key
    - 支持 Redis 存储（分布式）
    - 返回 429 Too Many Requests
    - 添加 header: X-RateLimit-Limit, X-RateLimit-Remaining
```

**优势**:
- API 保护
- 防止滥用
- 公平使用
- 成本控制

---

### 5. AuthenticationMiddleware ⚠️ (中优先级)
**功能**: 统一的认证处理

**业界实践**:
- JWT Token
- API Key
- OAuth 2.0

**实现要点**:
```python
class AuthenticationMiddleware:
    """Unified authentication handling."""

    - 支持多种认证方式
    - 注入用户信息到 request.state.user
    - 可配置白名单路径
    - 返回 401 Unauthorized
```

**注意**:
- 认证逻辑通常是业务特定的
- 框架应提供基础抽象，应用层实现具体逻辑

---

### 6. CORSMiddleware ℹ️ (已有 FastAPI 内置)
**状态**: FastAPI 已提供，无需重复实现

---

### 7. CompressionMiddleware ℹ️ (低优先级)
**功能**: 响应压缩（Gzip、Brotli）

**状态**: FastAPI/Starlette 已提供 GZipMiddleware

---

### 8. TimeoutMiddleware ⚠️ (中优先级)
**功能**: 请求超时控制

**实现要点**:
```python
class TimeoutMiddleware:
    """Request timeout handling."""

    - 设置请求超时时间
    - 超时返回 504 Gateway Timeout
    - 可配置不同路径的超时时间
```

**优势**:
- 防止慢请求占用资源
- 提高系统稳定性

---

### 9. MetricsMiddleware ⚠️ (中优先级)
**功能**: 指标收集（Prometheus、StatsD）

**实现要点**:
```python
class MetricsMiddleware:
    """Collect metrics for monitoring."""

    - 请求计数
    - 响应时间分布
    - 错误率
    - 集成 Prometheus/StatsD
```

---

### 10. TenantMiddleware ⚠️ (中优先级)
**功能**: 多租户识别和隔离

**实现要点**:
```python
class TenantMiddleware:
    """Multi-tenant identification."""

    - 从 header/subdomain/path 提取 tenant_id
    - 注入到 request.state.tenant_id
    - 用于数据隔离
```

---

## 实现优先级

### Phase 1: 核心可观测性（立即实现）
1. ✅ **IdempotencyMiddleware** - 已实现
2. 🔥 **RequestIDMiddleware** - 请求追踪
3. 🔥 **StructuredLoggingMiddleware** - 日志记录

### Phase 2: 安全和性能（高优先级）
4. 🔥 **RateLimitingMiddleware** - API 保护
5. ⚠️ **TimeoutMiddleware** - 超时控制

### Phase 3: 高级功能（中优先级）
6. ⚠️ **MetricsMiddleware** - 指标收集
7. ⚠️ **TenantMiddleware** - 多租户支持
8. ⚠️ **AuthenticationMiddleware** - 认证抽象

## 设计原则

1. **可选性**: 所有 middleware 都是可选的，应用可选择启用
2. **可配置**: 提供合理的默认值，支持自定义配置
3. **可扩展**: 提供抽象基类，支持应用层扩展
4. **性能**: 最小化性能开销
5. **标准化**: 遵循业界标准（HTTP headers、状态码等）

## 参考

- [FastAPI Middleware](https://fastapi.tiangolo.com/advanced/middleware/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [AWS API Gateway](https://docs.aws.amazon.com/apigateway/)
- [Stripe API Design](https://stripe.com/docs/api)
- [Google Cloud API Design](https://cloud.google.com/apis/design)
