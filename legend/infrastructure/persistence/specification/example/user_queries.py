"""User query examples.

This module provides practical examples of using the specification pattern
for common user-related queries.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from infrastructure.persistence.specification.core.type import SortDirection

from idp.framework.infrastructure.persistence.specification import (
    FilterOperator,
    Specification,
    SpecificationBuilder,
)


def find_active_users() -> Specification:
    """Find active users created in the last 30 days.

    Returns:
        Specification for finding active users, sorted by creation date.
    """
    return (SpecificationBuilder()
            .filter("is_active", True)
            .between("created_at",
                     datetime.now() - timedelta(days=30),
                     datetime.now())
            .add_sort("created_at", direction=SortDirection.DESC)
            .build())


def find_users_by_role(
    role: str,
    include_inactive: bool = False
) -> Specification:
    """Find users by role with basic information.

    Args:
        role: Role to filter by
        include_inactive: Whether to include inactive users

    Returns:
        Specification for finding users by role
    """
    builder = (SpecificationBuilder()
               .filter("role", role)
               .select("id", "name", "email", "role", "created_at"))

    if not include_inactive:
        builder.filter("is_active", True)

    return builder.build()


def search_users(
    search_text: str,
    roles: Optional[List[str]] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    page: int = 1,
    size: int = 20
) -> Specification:
    """Search users with various criteria.

    Args:
        search_text: Text to search in name or email
        roles: Optional list of roles to filter by
        min_age: Minimum age (inclusive)
        max_age: Maximum age (inclusive)
        page: Page number (0-based)
        size: Page size

    Returns:
        Specification for searching users
    """
    builder = SpecificationBuilder()

    # Text search
    builder.or_(
        lambda b: b.text_search("name", search_text),
        lambda b: b.text_search("email", search_text)
    )

    # Role filter
    if roles:
        builder.where("role", "in", roles)

    # Age range
    if min_age is not None or max_age is not None:
        builder.between("age", min_age or 0, max_age or 150)

    # Active users only
    builder.filter("is_active", True)

    # Select fields
    builder.select(
        "id", "name", "email", "role",
        "age", "created_at", "last_login"
    )

    # Include related data
    builder.include("profile", "permissions")

    # Sorting and pagination
    builder.add_sort("created_at", direction=SortDirection.DESC)
    builder.set_page(page=page, size=size)

    return builder.build()


def find_user_statistics(department: str) -> Specification:
    """Get user statistics by department.

    Args:
        department: Department to analyze

    Returns:
        Specification for user statistics
    """
    return (SpecificationBuilder()
            # Base filters
            .filter("department", department)
            .filter("is_active", True)

            # Group by role
            .group_by("role")

            # Statistics
            .count("id", alias="user_count")
            .avg("age", alias="average_age")
            .min("join_date", alias="earliest_join")
            .max("join_date", alias="latest_join")
            .group_concat("name", separator=", ", alias="user_names")

            # Having conditions
            .having("user_count", ">", 5)

            # Sort by count
            .add_sort("user_count", direction=SortDirection.DESC)
            .build())


def find_user_permissions(user_id: UUID) -> Specification:
    """Find user permissions with role information.

    Args:
        user_id: User ID to check

    Returns:
        Specification for finding user permissions
    """
    return (SpecificationBuilder()
            # Match user
            .filter("user_id", user_id)

            # Select permission fields
            .select(
            "id", "resource", "action",
            "granted_at", "expires_at"
    )

        # Include related data
        .include(
            "role.name",
            "role.permissions"
    )

        # Active permissions only
        .and_(
            lambda b: b.filter("is_active", True),
            lambda b: b.or_(
                lambda b: b.is_null("expires_at"),
                lambda b: b.where("expires_at", ">", datetime.now())
            )
    )

        # Sort by grant date
        .add_sort("granted_at", direction=SortDirection.DESC)
        .build())
