"""Catalog module queries."""

from contexts.catalog.application.queries.get_category import (
    GetCategoryQuery,
    GetCategoryHandler,
)
from contexts.catalog.application.queries.get_product import (
    GetProductQuery,
    GetProductHandler,
)
from contexts.catalog.application.queries.list_categories import (
    ListCategoriesQuery,
    ListCategoriesHandler,
)
from contexts.catalog.application.queries.list_products import (
    ListProductsQuery,
    ListProductsHandler,
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
]
