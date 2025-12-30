# Bento Framework Observability - P1/P2/P3 实施路线图

**创建日期**: 2024-12-30
**状态**: P1 完成 ✅ | P2/P3 待实施

---

## 📊 总体进度

| 优先级 | 任务 | 状态 | 完成度 |
|--------|------|------|--------|
| **P1** | 改造关键 Handler | ✅ 完成 | 100% |
| **P2** | HTTP TracingMiddleware | ⚠️ 待实施 | 0% |
| **P3** | OpenTelemetry 配置 | ⚠️ 待实施 | 0% |

---

## ✅ P1: 改造关键 Handler (已完成)

### 完成的工作

| Handler | 状态 | 改造内容 |
|---------|------|---------|
| **CreateOrderHandler** | ✅ | 完整的 tracing + metrics + logging |
| **PayOrderHandler** | ✅ | 完整的 tracing + metrics + logging |
| **CancelOrderHandler** | ✅ | 完整的 tracing + metrics + logging |
| **ShipOrderHandler** | ✅ | 完整的 tracing + metrics + logging |

### 改造效果

所有关键业务流程现在都有：
- ✅ 分布式追踪 (Distributed Tracing)
- ✅ 结构化日志 (Structured Logging)
- ✅ 业务指标 (Business Metrics)
- ✅ 异常记录 (Exception Recording)

### 代码示例

```python
from bento.application import ObservableCommandHandler

class CancelOrderHandler(ObservableCommandHandler[CancelOrderCommand, Order]):
    def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider):
        super().__init__(uow, observability, "ordering")

    async def handle(self, command: CancelOrderCommand) -> Order:
        async with self.tracer.start_span("cancel_order") as span:
            span.set_attribute("order_id", command.order_id)
            self.logger.info("Cancelling order", order_id=command.order_id)

            try:
                # ... business logic ...
                self._record_success("cancel_order", order_id=command.order_id)
                return order
            except Exception as e:
                self._record_failure("cancel_order", "error")
                raise
```

---

## ⚠️ P2: HTTP TracingMiddleware (待实施)

### 目标

自动追踪所有 HTTP 请求，零侵入业务代码。

### 实施方案

#### 步骤 1: 创建 TracingMiddleware

**文件**: `/workspace/bento/src/bento/runtime/middleware/tracing.py`

```python
"""HTTP Tracing Middleware - Automatic request tracing."""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from bento.application.ports.observability import ObservabilityProvider


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic HTTP request tracing.

    Automatically creates a span for each HTTP request with:
    - Request method, path, query params
    - Response status code
    - Request duration
    - Client IP

    Example:
        ```python
        from bento.runtime.middleware import TracingMiddleware

        observability = runtime.container.get("observability")
        app.add_middleware(
            TracingMiddleware,
            observability=observability,
        )
        ```
    """

    def __init__(self, app, observability: ObservabilityProvider):
        super().__init__(app)
        self.tracer = observability.get_tracer("http")
        self.meter = observability.get_meter("http")
        self.logger = observability.get_logger("http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request with tracing."""
        # Create span for this request
        async with self.tracer.start_span(f"{request.method} {request.url.path}") as span:
            # Set span attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.path", request.url.path)
            span.set_attribute("http.client_ip", request.client.host if request.client else "unknown")

            # Record request start
            start_time = time.time()

            try:
                # Process request
                response = await call_next(request)

                # Record success
                duration_ms = (time.time() - start_time) * 1000

                span.set_attribute("http.status_code", response.status_code)
                span.set_status("ok" if response.status_code < 400 else "error")

                # Record metrics
                counter = self.meter.create_counter("http_requests_total")
                counter.add(1, {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                })

                histogram = self.meter.create_histogram("http_request_duration_ms")
                histogram.record(duration_ms, {
                    "method": request.method,
                    "path": request.url.path,
                })

                # Log request
                self.logger.info(
                    "HTTP request completed",
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    duration_ms=duration_ms,
                )

                return response

            except Exception as e:
                # Record failure
                duration_ms = (time.time() - start_time) * 1000

                span.record_exception(e)
                span.set_status("error", str(e))

                counter = self.meter.create_counter("http_requests_failed")
                counter.add(1, {
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                })

                self.logger.error(
                    "HTTP request failed",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    duration_ms=duration_ms,
                )

                raise
```

#### 步骤 2: 导出 TracingMiddleware

**文件**: `/workspace/bento/src/bento/runtime/middleware/__init__.py`

```python
from bento.runtime.middleware.tracing import TracingMiddleware

__all__ = [
    # ... existing exports ...
    "TracingMiddleware",
]
```

#### 步骤 3: 集成到 my-shop

**文件**: `/workspace/bento/applications/my-shop/runtime/bootstrap_v2.py`

```python
from bento.runtime.middleware import TracingMiddleware

def create_fastapi_app(runtime: BentoRuntime) -> FastAPI:
    app = FastAPI(...)

    # Add tracing middleware (自动追踪所有请求)
    observability = runtime.container.get("observability")
    app.add_middleware(
        TracingMiddleware,
        observability=observability,
    )

    # ... other middleware ...

    return app
```

### 效果

添加 TracingMiddleware 后，所有 HTTP 请求都会自动追踪：

```
Span: GET /api/v1/orders/123
├─ http.method: GET
├─ http.path: /api/v1/orders/123
├─ http.status_code: 200
├─ http.client_ip: 192.168.1.100
└─ duration: 45ms
  └─ Span: create_order (from CreateOrderHandler)
      ├─ customer_id: customer-001
      └─ order_id: order-123
```

---

## ⚠️ P3: OpenTelemetry 配置支持 (待实施)

### 目标

支持通过配置文件启用/禁用 OpenTelemetry，方便在开发和生产环境切换。

### 实施方案

#### 步骤 1: 添加配置

**文件**: `/workspace/bento/applications/my-shop/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Observability settings
    observability_enabled: bool = Field(
        default=False,
        env="OBSERVABILITY_ENABLED",
        description="Enable observability (tracing/metrics)",
    )

    observability_provider: str = Field(
        default="noop",
        env="OBSERVABILITY_PROVIDER",
        description="Observability provider: noop or otel",
    )

    # OpenTelemetry settings
    otel_service_name: str = Field(
        default="my-shop",
        env="OTEL_SERVICE_NAME",
    )

    otel_trace_exporter: str = Field(
        default="console",
        env="OTEL_TRACE_EXPORTER",
        description="Trace exporter: console, jaeger, otlp",
    )

    otel_jaeger_host: str = Field(
        default="localhost",
        env="OTEL_JAEGER_HOST",
    )

    otel_jaeger_port: int = Field(
        default=6831,
        env="OTEL_JAEGER_PORT",
    )

    otel_metrics_exporter: str = Field(
        default="console",
        env="OTEL_METRICS_EXPORTER",
        description="Metrics exporter: console, prometheus, otlp",
    )

    otel_prometheus_port: int = Field(
        default=9090,
        env="OTEL_PROMETHEUS_PORT",
    )
```

#### 步骤 2: 条件注册 ObservabilityModule

**文件**: `/workspace/bento/applications/my-shop/runtime/bootstrap_v2.py`

```python
def build_runtime() -> BentoRuntime:
    """Build runtime with conditional observability."""

    modules = [
        InfraModule(),
        CatalogModule(),
        IdentityModule(),
        OrderingModule(),
        create_service_discovery_module(),
    ]

    # Add observability module based on configuration
    if settings.observability_enabled and settings.observability_provider == "otel":
        # Production: OpenTelemetry
        modules.append(
            ObservabilityModule(
                provider_type="otel",
                service_name=settings.otel_service_name,
                trace_exporter=settings.otel_trace_exporter,
                jaeger_host=settings.otel_jaeger_host,
                jaeger_port=settings.otel_jaeger_port,
                metrics_exporter=settings.otel_metrics_exporter,
                prometheus_port=settings.otel_prometheus_port,
            )
        )
    else:
        # Development: NoOp (zero overhead)
        modules.append(ObservabilityModule(provider_type="noop"))

    return (
        RuntimeBuilder()
        .with_config(
            service_name="my-shop",
            environment=settings.app_env,
        )
        .with_database(url=settings.database_url)
        .with_modules(*modules)
        .build_runtime()
    )
```

#### 步骤 3: 环境变量配置

**开发环境** (`.env.development`):
```bash
# Observability - NoOp (零开销)
OBSERVABILITY_ENABLED=false
OBSERVABILITY_PROVIDER=noop
```

**生产环境** (`.env.production`):
```bash
# Observability - OpenTelemetry
OBSERVABILITY_ENABLED=true
OBSERVABILITY_PROVIDER=otel

# Service name
OTEL_SERVICE_NAME=my-shop

# Tracing - Jaeger
OTEL_TRACE_EXPORTER=jaeger
OTEL_JAEGER_HOST=jaeger.observability.svc.cluster.local
OTEL_JAEGER_PORT=6831

# Metrics - Prometheus
OTEL_METRICS_EXPORTER=prometheus
OTEL_PROMETHEUS_PORT=9090
```

### 效果

- **开发环境**: 使用 NoOp provider，零开销
- **生产环境**: 使用 OpenTelemetry，完整的可观测性
- **一键切换**: 只需修改环境变量

---

## 📈 完整的 Observability 架构

### 三层追踪

```
┌─────────────────────────────────────────────┐
│  HTTP Layer (TracingMiddleware)            │ ← P2: 自动追踪所有请求
│  - 请求级别的 span                          │
│  - HTTP 指标 (status, duration)             │
└─────────────────────────────────────────────┘
              ↓ 自动创建子 span
┌─────────────────────────────────────────────┐
│  Application Layer (ObservableHandler)      │ ← P1: 业务流程追踪
│  - 业务级别的 span                          │
│  - 业务指标 (orders_created, etc.)          │
└─────────────────────────────────────────────┘
              ↓ 自动创建子 span
┌─────────────────────────────────────────────┐
│  Domain Layer                               │
│  - 纯业务逻辑 (无 observability)            │
└─────────────────────────────────────────────┘
```

### 追踪示例

```
Span: POST /api/v1/orders (HTTP Layer - P2)
├─ http.method: POST
├─ http.status_code: 201
├─ duration: 120ms
│
└─ Span: create_order (Application Layer - P1)
    ├─ customer_id: customer-001
    ├─ item_count: 2
    ├─ order_id: order-123
    ├─ order_total: 199.98
    └─ duration: 95ms
```

---

## 🎯 实施优先级

### 立即实施 (P1) ✅
- [x] CreateOrderHandler
- [x] PayOrderHandler
- [x] CancelOrderHandler
- [x] ShipOrderHandler

### 建议实施 (P2) ⚠️
- [ ] 创建 TracingMiddleware
- [ ] 集成到 my-shop
- [ ] 测试验证

### 可选实施 (P3) ⚠️
- [ ] 添加配置支持
- [ ] 环境变量配置
- [ ] 部署文档

---

## 📝 实施检查清单

### P1 检查清单 ✅
- [x] ObservableCommandHandler 基类已创建
- [x] CreateOrderHandler 已改造
- [x] PayOrderHandler 已改造
- [x] CancelOrderHandler 已改造
- [x] ShipOrderHandler 已改造
- [x] 所有测试通过

### P2 检查清单 ⚠️
- [ ] TracingMiddleware 已创建
- [ ] 导出到 bento.runtime.middleware
- [ ] 集成到 my-shop bootstrap
- [ ] 测试 HTTP 请求追踪
- [ ] 验证 span 嵌套关系

### P3 检查清单 ⚠️
- [ ] 配置类已更新
- [ ] 条件注册逻辑已实现
- [ ] 环境变量文件已创建
- [ ] 部署文档已更新
- [ ] 生产环境测试

---

## 🚀 下一步行动

### 立即行动
1. ✅ **P1 已完成** - 4 个关键 Handler 已改造

### 建议行动
2. ⚠️ **实施 P2** - 创建 TracingMiddleware
   - 时间估计: 1-2 小时
   - 收益: 自动追踪所有 HTTP 请求

3. ⚠️ **实施 P3** - 添加配置支持
   - 时间估计: 30 分钟
   - 收益: 方便在开发/生产环境切换

---

## 📚 参考文档

- `OBSERVABILITY_FRAMEWORK_REFACTORING.md` - Framework 改造文档
- `OBSERVABILITY_MY_SHOP_INTEGRATION.md` - my-shop 集成文档
- `bento/adapters/observability/README.md` - 使用指南

---

**创建时间**: 2024-12-30
**P1 状态**: ✅ **完成**
**P2/P3 状态**: ⚠️ **待实施**
