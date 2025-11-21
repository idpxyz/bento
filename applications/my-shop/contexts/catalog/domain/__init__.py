"""Catalog Domain Layer

包含商品目录的核心业务逻辑：
- 聚合根：Product, Category
- 端口：Repository interfaces
- 事件：领域事件定义
"""

from contexts.catalog.domain.category import Category
from contexts.catalog.domain.ports import (
    ICategoryRepository,
    IProductRepository,
)
from contexts.catalog.domain.product import Product

__all__ = [
    # Aggregates
    "Category",
    "Product",
    # Ports
    "ICategoryRepository",
    "IProductRepository",
]
