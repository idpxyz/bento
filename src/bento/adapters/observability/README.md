# Bento Observability - 使用指南

Bento Framework 的 Observability 实现，提供分布式追踪、指标收集和结构化日志。

---

## 🎯 快速开始

### 1. 基础使用（NoOp Provider）

```python
from bento.runtime import RuntimeBuilder
from bento.runtime.modules.observability import ObservabilityModule

# 开发环境 - 禁用 observability
runtime = (
    RuntimeBuilder()
    .with_config(service_name="my-shop", environment="dev")
    .with_modules(
        ObservabilityModule(provider_type="noop"),
        OrderingModule(),
    )
    .build_runtime()
)
```

### 2. 生产环境（OpenTelemetry）

```python
# 生产环境 - 启用 OpenTelemetry
runtime = (
    RuntimeBuilder()
    .with_config(service_name="my-shop", environment="prod")
    .with_modules(
        ObservabilityModule(
            provider_type="otel",
            service_name="my-shop",
            trace_exporter="jaeger",
            jaeger_host="localhost",
            jaeger_port=6831,
            metrics_exporter="prometheus",
        ),
        OrderingModule(),
    )
    .build_runtime()
)
```

---

## 📖 在应用中使用

### 1. 在 Application Service 中使用

```python
from bento.application.ports.observability import ObservabilityProvider

class OrderService:
    def __init__(self, observability: ObservabilityProvider):
        self.tracer = observability.get_tracer("order-service")
        self.meter = observability.get_meter("order-service")
        self.logger = observability.get_logger("order-service")

    async def create_order(self, command: CreateOrderCommand):
        # 分布式追踪
        async with self.tracer.start_span("create_order") as span:
            span.set_attribute("order_id", command.order_id)
            span.set_attribute("customer_id", command.customer_id)

            # 结构化日志
            self.logger.info(
                "Creating order",
                order_id=command.order_id,
                customer_id=command.customer_id,
                total=command.total,
            )

            try:
                # 业务逻辑
                order = await self._create_order_logic(command)

                # 指标收集
                counter = self.meter.create_counter("orders_created")
                counter.add(1, {"status": "success"})

                histogram = self.meter.create_histogram("order_value")
                histogram.record(command.total, {"currency": "USD"})

                span.set_status("ok")
                return order

            except Exception as e:
                # 记录异常
                span.record_exception(e)
                span.set_status("error", str(e))

                self.logger.error(
                    "Failed to create order",
                    order_id=command.order_id,
                    error=str(e),
                )

                counter = self.meter.create_counter("orders_failed")
                counter.add(1, {"error_type": type(e).__name__})

                raise
```

### 2. 在 Module 中注入

```python
from bento.runtime import BentoModule

class OrderingModule(BentoModule):
    name = "ordering"
    requires = ["observability"]  # 声明依赖

    async def on_register(self, container):
        # 获取 observability provider
        observability = container.get("observability")

        # 创建 service
        order_service = OrderService(observability)

        # 注册到容器
        container.set("order.service", order_service)
```

---

## 🔧 配置选项

### NoOp Provider

```python
ObservabilityModule(
    provider_type="noop",
)
```

**用途**: 开发环境、测试环境，或禁用 observability

### OpenTelemetry Provider

#### Console 导出器（开发）

```python
ObservabilityModule(
    provider_type="otel",
    service_name="my-shop",
    trace_exporter="console",
    metrics_exporter="console",
)
```

#### Jaeger 导出器（生产）

```python
ObservabilityModule(
    provider_type="otel",
    service_name="my-shop",
    trace_exporter="jaeger",
    jaeger_host="jaeger.observability.svc.cluster.local",
    jaeger_port=6831,
)
```

#### OTLP 导出器（生产）

```python
ObservabilityModule(
    provider_type="otel",
    service_name="my-shop",
    trace_exporter="otlp",
    otlp_endpoint="http://otel-collector:4317",
    metrics_exporter="otlp",
)
```

#### Prometheus 导出器（生产）

```python
ObservabilityModule(
    provider_type="otel",
    service_name="my-shop",
    trace_exporter="jaeger",
    jaeger_host="localhost",
    jaeger_port=6831,
    metrics_exporter="prometheus",
    prometheus_prefix="myshop_",
)
```

---

## 📊 API 参考

### ObservabilityProvider

```python
class ObservabilityProvider(Protocol):
    def get_tracer(self, name: str) -> Tracer: ...
    def get_meter(self, name: str) -> Meter: ...
    def get_logger(self, name: str) -> Logger: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

### Tracer

```python
class Tracer(Protocol):
    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Any: ...  # Returns context manager
```

### Span

```python
class Span(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def set_status(self, status: str, description: str = "") -> None: ...
    def record_exception(self, exception: Exception) -> None: ...
    def end(self) -> None: ...
```

### Meter

```python
class Meter(Protocol):
    def create_counter(self, name: str, description: str = "") -> Counter: ...
    def create_gauge(self, name: str, description: str = "") -> Gauge: ...
    def create_histogram(self, name: str, description: str = "") -> Histogram: ...
```

### Counter / Gauge / Histogram

```python
class Counter(Protocol):
    def add(self, value: float, attributes: dict[str, Any] | None = None) -> None: ...

class Gauge(Protocol):
    def set(self, value: float, attributes: dict[str, Any] | None = None) -> None: ...

class Histogram(Protocol):
    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None: ...
```

### Logger

```python
class Logger(Protocol):
    def debug(self, message: str, **context: Any) -> None: ...
    def info(self, message: str, **context: Any) -> None: ...
    def warning(self, message: str, **context: Any) -> None: ...
    def error(self, message: str, **context: Any) -> None: ...
    def critical(self, message: str, **context: Any) -> None: ...
```

---

## 🚀 最佳实践

### 1. Span 命名

```python
# ✅ 好的命名
async with tracer.start_span("create_order"):
    pass

async with tracer.start_span("payment.process"):
    pass

# ❌ 避免的命名
async with tracer.start_span("do_something"):
    pass
```

### 2. 属性添加

```python
# ✅ 添加有意义的属性
async with tracer.start_span("create_order") as span:
    span.set_attribute("order_id", order.id)
    span.set_attribute("customer_id", order.customer_id)
    span.set_attribute("total", order.total)
    span.set_attribute("item_count", len(order.items))
```

### 3. 指标命名

```python
# ✅ 遵循命名约定
counter = meter.create_counter("http_requests_total")
histogram = meter.create_histogram("http_request_duration_seconds")
gauge = meter.create_gauge("active_connections")

# ❌ 避免的命名
counter = meter.create_counter("requests")
histogram = meter.create_histogram("time")
```

### 4. 结构化日志

```python
# ✅ 使用结构化上下文
logger.info(
    "Order created",
    order_id=order.id,
    customer_id=order.customer_id,
    total=order.total,
)

# ❌ 避免字符串拼接
logger.info(f"Order {order.id} created for customer {order.customer_id}")
```

---

## 🔌 依赖安装

### 基础（必需）

```bash
# Bento Framework 已包含
```

### OpenTelemetry（可选）

```bash
# 基础包
pip install opentelemetry-api opentelemetry-sdk

# Jaeger 导出器
pip install opentelemetry-exporter-jaeger

# OTLP 导出器
pip install opentelemetry-exporter-otlp

# Prometheus 导出器
pip install opentelemetry-exporter-prometheus
```

---

## 📁 架构设计

```
Application Layer
    ↓ depends on
Application Ports (bento.application.ports.observability)
    ↑ implements
Adapters (bento.adapters.observability)
    ├─ NoOpObservabilityProvider
    └─ OpenTelemetryProvider
```

**设计原则**:
- ✅ 遵循六边形架构
- ✅ 端口与适配器模式
- ✅ 依赖反转原则
- ✅ 完全可替换

---

## 🎓 示例项目

查看 `applications/my-shop` 获取完整示例。

---

**文档版本**: 1.0.0
**最后更新**: 2024-12-30
