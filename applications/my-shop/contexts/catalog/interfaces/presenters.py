"""Presenters for converting domain objects to API responses."""

from contexts.catalog.domain.models.product import Product


def product_to_dict(product: Product) -> dict:
    """Convert Product aggregate to dictionary for API response."""
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "sku": product.sku,
        "brand": product.brand,
        "is_active": product.is_active,
        "sales_count": product.sales_count,
        "category_id": str(product.category_id) if product.category_id else None,
        "is_categorized": product.is_categorized(),
    }
