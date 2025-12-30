# Service Discovery 集成指南

本文档说明如何在 my-shop 应用中使用 Bento Framework 的服务发现功能。

## 📋 概述

my-shop 应用已集成 Bento Runtime 的服务发现模块，支持三种后端：

1. **ENV** - 基于环境变量的服务发现（开发环境推荐）
2. **Kubernetes** - 基于 Kubernetes DNS 的服务发现（K8s 环境）
3. **Consul** - 基于 Consul 的服务发现（生产环境推荐）

## 🚀 快速开始

### 1. 配置服务发现后端

在 `.env` 文件中配置服务发现后端：

```bash
# 选择后端类型
SERVICE_DISCOVERY_BACKEND=env  # 可选: env, consul, kubernetes

# 通用配置
SERVICE_DISCOVERY_TIMEOUT=5
SERVICE_DISCOVERY_RETRY=3
SERVICE_DISCOVERY_CACHE_TTL=300
```

### 2. ENV 后端配置（开发环境）

使用环境变量定义服务地址：

```bash
SERVICE_DISCOVERY_BACKEND=env

# 定义服务 URL
SERVICE_CATALOG_SERVICE_URL=http://catalog-service:8001
SERVICE_ORDER_SERVICE_URL=http://order-service:8002
SERVICE_PAYMENT_SERVICE_URL=http://payment-service:8003
SERVICE_INVENTORY_SERVICE_URL=http://inventory-service:8004
```

**命名规则**：`SERVICE_<服务名大写>_URL`
- `catalog-service` → `SERVICE_CATALOG_SERVICE_URL`
- `order-service` → `SERVICE_ORDER_SERVICE_URL`

### 3. Kubernetes 后端配置

在 Kubernetes 环境中使用 DNS 服务发现：

```bash
SERVICE_DISCOVERY_BACKEND=kubernetes

# Kubernetes 配置
KUBERNETES_NAMESPACE=default
KUBERNETES_SERVICE_SUFFIX=svc.cluster.local
```

服务将通过 Kubernetes DNS 解析：
- `catalog-service` → `catalog-service.default.svc.cluster.local`

### 4. Consul 后端配置

使用 Consul 作为服务注册中心：

```bash
SERVICE_DISCOVERY_BACKEND=consul

# Consul 配置
CONSUL_URL=http://consul:8500
CONSUL_DATACENTER=dc1
```

## 💻 使用方式

### 方式 1: 在 Command/Query Handler 中使用

```python
from bento.application import ApplicationService
from bento.application.ports.uow import UnitOfWork
from shared.services.external_service_client import ExternalServiceClient


class GetProductDetailsHandler(ApplicationService):
    """获取产品详情（含外部服务调用）"""

    async def execute(self, product_id: str) -> dict:
        # 从容器获取服务发现
        discovery = self.container.get("service.discovery")
        client = ExternalServiceClient(discovery)

        try:
            # 调用 catalog-service 获取产品信息
            product = await client.call_service(
                service_name="catalog-service",
                path=f"/api/v1/products/{product_id}",
                method="GET"
            )

            # 调用 inventory-service 获取库存信息
            inventory = await client.call_service(
                service_name="inventory-service",
                path=f"/api/v1/inventory/{product_id}",
                method="GET"
            )

            return {
                "product": product,
                "inventory": inventory
            }
        finally:
            await client.close()
```

### 方式 2: 直接使用 ServiceDiscovery

```python
from bento.application.ports.service_discovery import ServiceDiscovery


async def call_external_service(container):
    """直接使用服务发现"""
    discovery: ServiceDiscovery = container.get("service.discovery")

    # 发现服务实例
    instance = await discovery.discover("catalog-service")

    print(f"Service: {instance.service_name}")
    print(f"Host: {instance.host}")
    print(f"Port: {instance.port}")
    print(f"URL: {instance.scheme}://{instance.host}:{instance.port}")
```

### 方式 3: 在 FastAPI 路由中使用

```python
from fastapi import APIRouter, Depends
from runtime.bootstrap_v2 import get_runtime

router = APIRouter()


@router.get("/external/products/{product_id}")
async def get_external_product(product_id: str):
    """调用外部服务获取产品"""
    runtime = get_runtime()
    discovery = runtime.container.get("service.discovery")

    # 发现服务
    instance = await discovery.discover("catalog-service")

    # 构建 URL 并调用
    url = f"{instance.scheme}://{instance.host}:{instance.port}/api/v1/products/{product_id}"

    # 使用 httpx 或其他 HTTP 客户端调用
    # ...

    return {"url": url}
```

## 🔧 高级功能

### 服务注册

```python
# 注册当前服务到服务发现
discovery = container.get("service.discovery")

await discovery.register(
    service_name="my-shop",
    host="localhost",
    port=8000,
    metadata={
        "version": "1.0.0",
        "environment": "production"
    }
)
```

### 服务注销

```python
# 应用关闭时注销服务
await discovery.deregister(
    service_name="my-shop",
    host="localhost",
    port=8000
)
```

### 健康检查

```python
# 检查服务健康状态
is_healthy = await discovery.health_check(
    service_name="catalog-service"
)

if is_healthy:
    print("Service is healthy")
```

## 📊 缓存机制

服务发现结果会自动缓存，默认 TTL 为 300 秒（5 分钟）。

```bash
# 调整缓存 TTL（秒）
SERVICE_DISCOVERY_CACHE_TTL=600  # 10 分钟
```

缓存的好处：
- ✅ 减少服务发现请求
- ✅ 提高响应速度
- ✅ 降低注册中心负载

## 🧪 测试

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_service_discovery(mocker):
    """测试服务发现功能"""
    # Mock 服务发现
    mock_discovery = AsyncMock()
    mock_discovery.discover.return_value = ServiceInstance(
        service_name="catalog-service",
        host="localhost",
        port=8001,
        scheme="http"
    )

    # 测试逻辑
    instance = await mock_discovery.discover("catalog-service")
    assert instance.host == "localhost"
```

### 集成测试

参考 `tests/integration/test_service_discovery_integration.py`

## 🐛 故障排查

### 问题 1: ServiceNotFoundError

**原因**：服务未配置或名称不匹配

**解决**：
1. 检查环境变量是否正确设置
2. 确认服务名称格式（使用 `-` 而非 `_`）
3. 查看日志确认后端类型

### 问题 2: 连接超时

**原因**：服务不可达或网络问题

**解决**：
1. 检查服务是否运行
2. 验证网络连通性
3. 调整超时配置：`SERVICE_DISCOVERY_TIMEOUT=10`

### 问题 3: Consul 连接失败

**原因**：Consul 服务未启动或 URL 错误

**解决**：
1. 确认 Consul 服务运行：`curl http://consul:8500/v1/status/leader`
2. 检查 `CONSUL_URL` 配置
3. 验证网络和防火墙规则

## 📚 最佳实践

### 1. 环境隔离

不同环境使用不同的服务发现后端：

```bash
# 开发环境
SERVICE_DISCOVERY_BACKEND=env

# 测试环境
SERVICE_DISCOVERY_BACKEND=kubernetes

# 生产环境
SERVICE_DISCOVERY_BACKEND=consul
```

### 2. 错误处理

```python
from bento.application.ports.service_discovery import ServiceNotFoundError

try:
    instance = await discovery.discover("catalog-service")
except ServiceNotFoundError as e:
    logger.error(f"Service not found: {e}")
    # 降级处理或返回错误
    return {"error": "Service unavailable"}
```

### 3. 资源清理

```python
client = ExternalServiceClient(discovery)
try:
    result = await client.call_service(...)
finally:
    await client.close()  # 确保关闭 HTTP 客户端
```

### 4. 监控和日志

```python
import logging

logger = logging.getLogger(__name__)

# 记录服务发现日志
logger.info(f"Discovering service: {service_name}")
instance = await discovery.discover(service_name)
logger.info(f"Found service at {instance.host}:{instance.port}")
```

## 🔗 相关文档

- [Bento Service Discovery README](/workspace/bento/src/bento/adapters/service_discovery/README.md)
- [Service Discovery 实现总结](/workspace/BENTO-SERVICE-DISCOVERY-IMPLEMENTATION-SUMMARY.md)
- [Runtime 模块测试](/workspace/bento/tests/unit/runtime/test_service_discovery_module.py)

## 📞 支持

如有问题，请查看：
1. 应用日志：检查服务发现相关日志
2. 运行测试：`pytest tests/integration/test_service_discovery_integration.py`
3. 查看示例：`shared/services/external_service_client.py`
