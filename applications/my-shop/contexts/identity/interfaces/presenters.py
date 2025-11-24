"""Presenters for converting domain objects to API responses."""

from contexts.identity.domain.models.user import User


def user_to_dict(user: User) -> dict:
    """Convert User aggregate to dictionary for API response.

    Args:
        user: User aggregate

    Returns:
        Dictionary representation
    """
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }
