"""Catalog module queries."""

from contexts.catalog.application.queries.get_category import (
    GetCategoryHandler,
    GetCategoryQuery,
)
from contexts.catalog.application.queries.get_category_tree import (
    CategoryTreeNodeDTO,
    GetCategoryTreeHandler,
    GetCategoryTreeQuery,
)
from contexts.catalog.application.queries.get_product import (
    GetProductHandler,
    GetProductQuery,
)
from contexts.catalog.application.queries.list_categories import (
    ListCategoriesHandler,
    ListCategoriesQuery,
)
from contexts.catalog.application.queries.list_products import (
    ListProductsHandler,
    ListProductsQuery,
)

__all__ = [
    # Product queries
    "GetProductQuery",
    "GetProductHandler",
    "ListProductsQuery",
    "ListProductsHandler",
    # Category queries
    "GetCategoryQuery",
    "GetCategoryHandler",
    "ListCategoriesQuery",
    "ListCategoriesHandler",
    "GetCategoryTreeQuery",
    "GetCategoryTreeHandler",
    "CategoryTreeNodeDTO",
]
