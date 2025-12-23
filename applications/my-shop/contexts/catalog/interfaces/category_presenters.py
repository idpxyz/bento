"""Presenters for converting category domain objects to API responses."""

from contexts.catalog.domain.models.category import Category


def category_to_dict(category: Category) -> dict:
    """Convert Category aggregate to dictionary for API response."""
    return {
        "id": str(category.id),
        "name": category.name,
        "description": category.description,
        "parent_id": str(category.parent_id) if category.parent_id else None,
        "is_root": category.is_root(),
    }
