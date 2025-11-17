"""Presenters for converting domain objects to API responses."""

from contexts.catalog.domain.product import Product


def product_to_dict(product: Product) -> dict:
    """Convert Product aggregate to dictionary for API response."""
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
    }
