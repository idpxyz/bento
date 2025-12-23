"""Security models for Bento Framework.

This module provides core security models used across the security module.

Example:
    ```python
    from bento.security import CurrentUser

    user = CurrentUser(
        id="user-123",
        permissions=["orders:read", "orders:write"],
        roles=["admin"],
    )

    if user.has_permission("orders:write"):
        # User can write orders
        ...
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CurrentUser:
    """Represents the currently authenticated user.

    This is a framework-agnostic user representation that can be
    populated from any authentication provider (JWT, OAuth, etc.)

    Attributes:
        id: Unique user identifier
        permissions: List of permission strings (e.g., "orders:read")
        roles: List of role names (e.g., "admin", "user")
        metadata: Additional user data from the auth provider

    Example:
        ```python
        user = CurrentUser(
            id="user-123",
            permissions=["orders:read", "orders:write"],
            roles=["admin"],
            metadata={"email": "user@example.com"},
        )

        # Check permissions
        user.has_permission("orders:read")  # True
        user.has_any_permission(["orders:read", "products:read"])  # True
        user.has_all_permissions(["orders:read", "orders:write"])  # True

        # Check roles
        user.has_role("admin")  # True
        ```
    """

    id: str
    permissions: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: Permission string to check

        Returns:
            True if user has the permission
        """
        return permission in self.permissions

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has at least one of the permissions
        """
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: list[str]) -> bool:
        """Check if user has all of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has all of the permissions
        """
        return all(p in self.permissions for p in permissions)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role.

        Args:
            role: Role name to check

        Returns:
            True if user has the role
        """
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles.

        Args:
            roles: List of roles to check

        Returns:
            True if user has at least one of the roles
        """
        return any(r in self.roles for r in roles)
