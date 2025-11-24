"""Category Repository Interface - Secondary Port

定义商品分类聚合根的持久化契约。
遵循 Repository 模式和 Dependency Inversion Principle。
"""

from __future__ import annotations

from typing import Protocol

from bento.core.ids import ID
from bento.domain.ports.repository import IRepository

from contexts.catalog.domain.category import Category


class ICategoryRepository(IRepository[Category, ID], Protocol):
    """Category repository interface (Secondary Port).

    继承 Bento 的 Repository[Category, ID] 协议自动获得标准方法：
    - async def get(id: ID) -> Category | None
    - async def save(entity: Category) -> Category
    - async def delete(entity: Category) -> None
    - async def find_all() -> list[Category]
    - async def exists(id: ID) -> bool
    - async def count() -> int

    Domain-specific query methods:
    """

    async def find_by_name(self, name: str) -> Category | None:
        """Find category by exact name.

        Args:
            name: Category name

        Returns:
            Category if found, None otherwise
        """
        ...

    async def find_root_categories(self) -> list[Category]:
        """Find all root categories (categories without parent).

        Returns:
            List of root categories
        """
        ...

    async def find_subcategories(self, parent_id: ID) -> list[Category]:
        """Find subcategories of a parent category.

        Args:
            parent_id: Parent category identifier

        Returns:
            List of subcategories
        """
        ...
