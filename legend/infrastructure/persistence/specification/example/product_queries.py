"""Product query examples.

This module provides practical examples of using the specification pattern
for common product-related queries.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from infrastructure.persistence.specification.core.type import SortDirection

from idp.framework.infrastructure.persistence.specification import (
    FilterOperator,
    Specification,
    SpecificationBuilder,
)


def find_available_products(
    category: Optional[str] = None,
    min_stock: int = 1
) -> Specification:
    """Find available products with optional category filter.

    Args:
        category: Optional product category
        min_stock: Minimum stock level required

    Returns:
        Specification for finding available products
    """
    builder = (SpecificationBuilder()
               .filter("is_active", True)
               .where("stock_level", ">=", min_stock)
               .select(
        "id", "sku", "name", "category",
        "price", "stock_level", "rating"
    ))

    if category:
        builder.filter("category", category)

    return (builder
            .add_sort("name")
            .build())


def search_products(
    search_text: str,
    categories: Optional[List[str]] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    min_rating: Optional[float] = None,
    tags: Optional[List[str]] = None,
    page: int = 0,
    size: int = 20
) -> Specification:
    """Search products with various criteria.

    Args:
        search_text: Text to search in name or description
        categories: Optional list of categories to filter by
        min_price: Minimum price
        max_price: Maximum price
        min_rating: Minimum rating threshold
        tags: Required product tags
        page: Page number (0-based)
        size: Page size

    Returns:
        Specification for searching products
    """
    builder = SpecificationBuilder()

    # Text search
    builder.or_(
        lambda b: b.text_search("name", search_text),
        lambda b: b.text_search("description", search_text)
    )

    # Category filter
    if categories:
        builder.where("category", "in", categories)

    # Price range
    if min_price is not None or max_price is not None:
        builder.between(
            "price",
            min_price or Decimal('0'),
            max_price or Decimal('999999999.99')
        )

    # Rating filter
    if min_rating is not None:
        builder.where("rating", ">=", min_rating)

    # Tag filter
    if tags:
        builder.array_contains("tags", tags)

    # Active products only
    builder.filter("is_active", True)

    # Select fields and includes
    builder.select(
        "id", "sku", "name", "description",
        "category", "price", "stock_level",
        "rating", "tags"
    )

    builder.include(
        "images",
        "variants",
        "manufacturer"
    )

    # Sorting and pagination
    return (builder
            .add_sort("rating", direction=SortDirection.DESC)
            .add_sort("name")
            .set_page(page=page+1, size=size)
            .build())


def find_product_statistics(
    category: Optional[str] = None
) -> Specification:
    """Get product statistics with optional category filter.

    Args:
        category: Optional category to analyze

    Returns:
        Specification for product statistics
    """
    builder = (SpecificationBuilder()
               .filter("is_active", True))

    if category:
        builder.filter("category", category)

    return (builder
            # Group by category
            .group_by("category")

            # Statistics
            .count("id", alias="product_count")
            .sum("stock_level", alias="total_stock")
            .avg("price", alias="average_price")
            .avg("rating", alias="average_rating")
            .min("price", alias="min_price")
            .max("price", alias="max_price")

            # Having condition
            .having("product_count", ">", 0)

            # Sort by count
            .add_sort("product_count", direction=SortDirection.DESC)
            .build())


def find_low_stock_products(
    threshold: int = 10,
    include_variants: bool = True
) -> Specification:
    """Find products with low stock levels.

    Args:
        threshold: Stock level threshold
        include_variants: Whether to include product variants

    Returns:
        Specification for finding low stock products
    """
    builder = (SpecificationBuilder()
               # Stock threshold
               .where("stock_level", "<=", threshold)
               .filter("is_active", True)

               # Basic fields
               .select(
        "id", "sku", "name", "category",
        "price", "stock_level", "reorder_level"
    ))

    # Include variants if requested
    if include_variants:
        builder.include(
            "variants.sku",
            "variants.name",
            "variants.stock_level"
        )

    return (builder
            .add_sort("stock_level")
            .build())


def find_trending_products(
    min_rating: float = 4.0,
    min_reviews: int = 10
) -> Specification:
    """Find trending products based on ratings and reviews.

    Args:
        min_rating: Minimum average rating
        min_reviews: Minimum number of reviews

    Returns:
        Specification for finding trending products
    """
    return (SpecificationBuilder()
            # Rating and review criteria
            .where("rating", ">=", min_rating)
            .where("review_count", ">=", min_reviews)
            .filter("is_active", True)

            # Select fields
            .select(
            "id", "sku", "name", "category",
            "price", "rating", "review_count",
            "stock_level"
    )

        # Include related data
        .include(
            "images",
            "reviews.rating",
            "reviews.comment"
    )

        # Sort by rating and review count
        .add_sort("rating", direction=SortDirection.DESC)
        .add_sort("review_count", direction=SortDirection.DESC)
        .build())
