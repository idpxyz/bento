"""Catalog Domain Ports

定义 Catalog bounded context 的所有端口（接口）。
遵循 Hexagonal Architecture 和 Dependency Inversion Principle。

Secondary Ports (被驱动端口):
- Repository interfaces: 数据持久化契约
- Service interfaces: 外部服务契约

Primary Ports (驱动端口):
- 由 Application Layer 的 Use Cases 定义
"""

from contexts.catalog.domain.ports.repositories import (
    ICategoryRepository,
    IProductRepository,
)

# 服务接口（目前为空，未来扩展）
# from contexts.catalog.domain.ports.services import (...)

__all__ = [
    # Repository Ports
    "ICategoryRepository",
    "IProductRepository",
    # Service Ports (future expansion)
    # ...
]
