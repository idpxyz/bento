"""Presenters for converting category domain objects to API responses."""

from contexts.catalog.domain.category import Category


def category_to_dict(category: Category) -> dict:
    """Convert Category aggregate to dictionary for API response."""
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "is_root": category.is_root(),
    }
