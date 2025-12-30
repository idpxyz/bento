# Service Discovery 服务发现

Bento Framework 的服务发现实现，支持多种后端（环境变量、Consul、Kubernetes）。

## 快速开始

### 1. 环境变量方式（开发环境）

```python
from bento.runtime import RuntimeBuilder
from bento.adapters.service_discovery import (
    ServiceDiscoveryModule,
    ServiceDiscoveryConfig,
    ServiceDiscoveryBackend,
)

# 配置
config = ServiceDiscoveryConfig(backend=ServiceDiscoveryBackend.ENV)

# 创建 Runtime
runtime = (
    RuntimeBuilder()
    .with_config(service_name="order-service", environment="dev")
    .with_modules(
        ServiceDiscoveryModule(config),
        OrderingModule(),
    )
    .build_runtime()
)

app = runtime.create_fastapi_app()
```

**环境变量配置**:
```bash
SERVICE_CATALOG_SERVICE_URL=http://localhost:8002
SERVICE_PAYMENT_SERVICE_URL=http://localhost:8003
```

### 2. Kubernetes 方式（生产环境）

```python
from bento.adapters.service_discovery import (
    ServiceDiscoveryModule,
    ServiceDiscoveryConfig,
    ServiceDiscoveryBackend,
)

config = ServiceDiscoveryConfig(
    backend=ServiceDiscoveryBackend.KUBERNETES,
    kubernetes_namespace="default",
)

runtime = (
    RuntimeBuilder()
    .with_modules(
        ServiceDiscoveryModule(config),
        OrderingModule(),
    )
    .build_runtime()
)
```

### 3. 在模块中使用

```python
from bento.runtime import BentoModule
from bento.application.ports import ServiceDiscovery

class OrderingModule(BentoModule):
    name = "ordering"
    requires = ["service_discovery"]

    async def on_register(self, container):
        # 获取服务发现
        service_discovery: ServiceDiscovery = container.get("service.discovery")

        # 发现目录服务
        catalog_instance = await service_discovery.discover("catalog-service")

        # 创建客户端
        catalog_client = CatalogServiceClient(base_url=catalog_instance.url)
        container.set("catalog.client", catalog_client)
```

## 支持的后端

### EnvServiceDiscovery（环境变量）

**优点**:
- 简单易用
- 无需外部依赖
- 适合开发环境

**配置**:
```bash
SERVICE_SERVICE_NAME_URL=http://host:port
```

### KubernetesServiceDiscovery（Kubernetes）

**优点**:
- 自动服务发现
- 内置负载均衡
- 自动故障转移

**配置**:
```python
ServiceDiscoveryConfig(
    backend=ServiceDiscoveryBackend.KUBERNETES,
    kubernetes_namespace="default",
)
```

### ConsulServiceDiscovery（Consul）

**优点**:
- 功能完整
- 支持健康检查
- 支持自定义元数据

**配置**:
```python
ServiceDiscoveryConfig(
    backend=ServiceDiscoveryBackend.CONSUL,
    consul_url="http://localhost:8500",
)
```

**注意**: 需要安装 `aiohttp` 依赖

## 缓存机制

所有服务发现都自动添加缓存装饰器，减少对服务发现系统的调用。

```python
# 缓存配置
config = ServiceDiscoveryConfig(
    backend=ServiceDiscoveryBackend.ENV,
    cache_ttl=300,  # 缓存 5 分钟
)
```

## API 参考

### ServiceDiscovery 接口

```python
class ServiceDiscovery(ABC):
    async def discover(
        self,
        service_name: str,
        strategy: str = "round_robin"
    ) -> ServiceInstance:
        """发现单个服务实例"""
        pass

    async def discover_all(
        self,
        service_name: str
    ) -> list[ServiceInstance]:
        """发现所有服务实例"""
        pass

    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """注册服务"""
        pass

    async def deregister(
        self,
        service_name: str,
        host: str,
        port: int
    ) -> None:
        """注销服务"""
        pass

    async def health_check(
        self,
        service_name: str,
        host: str,
        port: int
    ) -> bool:
        """检查服务健康状态"""
        pass
```

### ServiceInstance 对象

```python
@dataclass
class ServiceInstance:
    service_name: str
    host: str
    port: int
    scheme: str = "http"
    metadata: dict | None = None

    @property
    def url(self) -> str:
        """获取完整 URL"""
        return f"{self.scheme}://{self.host}:{self.port}"
```

## 错误处理

```python
from bento.application.ports import ServiceNotFoundError

try:
    instance = await service_discovery.discover("unknown-service")
except ServiceNotFoundError as e:
    logger.error(f"Service not found: {e}")
```

## 最佳实践

### 1. 根据环境选择后端

```python
import os

backend_str = os.getenv("SERVICE_DISCOVERY_BACKEND", "env")
config = ServiceDiscoveryConfig(
    backend=ServiceDiscoveryBackend(backend_str)
)
```

### 2. 缓存优化

```python
# 生产环境使用较长的缓存时间
config = ServiceDiscoveryConfig(
    backend=ServiceDiscoveryBackend.KUBERNETES,
    cache_ttl=600,  # 10 分钟
)
```

### 3. 错误处理

```python
async def get_service_instance(service_name: str):
    try:
        return await service_discovery.discover(service_name)
    except ServiceNotFoundError:
        logger.error(f"Service {service_name} not found")
        # 使用备用地址或重试
        return None
```

## 测试

```python
from bento.adapters.service_discovery.tests.test_service_discovery import MockServiceDiscovery

# 在测试中使用 Mock
mock_discovery = MockServiceDiscovery(
    instances={
        "catalog-service": [
            ServiceInstance(
                service_name="catalog-service",
                host="localhost",
                port=8002,
            )
        ]
    }
)

container.set("service.discovery", mock_discovery)
```

## 文件结构

```
bento/adapters/service_discovery/
├── __init__.py                 # 导出
├── config.py                   # 配置对象
├── env.py                      # 环境变量实现
├── kubernetes.py               # Kubernetes 实现
├── consul.py                   # Consul 实现
├── cached.py                   # 缓存装饰器
├── README.md                   # 本文件
└── tests/
    ├── __init__.py
    └── test_service_discovery.py
```

## 相关文档

- [Bento Framework 服务发现设计](../../../BENTO-FRAMEWORK-SERVICE-DISCOVERY-DESIGN.md)
- [微服务架构支持](../../../BENTO-RUNTIME-MICROSERVICES-SUPPORT.md)
- [Runtime 使用指南](../../runtime/USAGE.md)
