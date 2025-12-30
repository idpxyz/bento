"""Product Repository Interface - Secondary Port

定义商品聚合根的持久化契约。
遵循 Repository 模式和 Dependency Inversion Principle。
"""

from __future__ import annotations

from typing import Protocol

from bento.core.ids import ID
from bento.domain.ports.repository import IRepository

from contexts.catalog.domain.models.product import Product


class IProductRepository(IRepository[Product, ID], Protocol):
    """Product repository interface (Secondary Port).

    继承 Bento 的 Repository[Product, ID] 协议自动获得标准方法：
    - async def get(id: ID) -> Product | None
    - async def save(entity: Product) -> Product
    - async def delete(entity: Product) -> None
    - async def find_all() -> list[Product]
    - async def exists(id: ID) -> bool
    - async def count() -> int

    Domain-specific query methods:
    """

    async def find_by_category(self, category_id: ID) -> list[Product]:
        """Find products by category ID.

        Args:
            category_id: Category identifier

        Returns:
            List of products in the category
        """
        ...

    async def find_by_name(self, name: str) -> list[Product]:
        """Find products by name (fuzzy search).

        Args:
            name: Product name to search for

        Returns:
            List of products matching the name
        """
        ...

    async def find_in_stock(self) -> list[Product]:
        """Find products that are in stock.

        Returns:
            List of products with stock > 0
        """
        ...

    async def find_by_price_range(self, min_price: float, max_price: float) -> list[Product]:
        """Find products within price range.

        Args:
            min_price: Minimum price (inclusive)
            max_price: Maximum price (inclusive)

        Returns:
            List of products within the price range
        """
        ...
