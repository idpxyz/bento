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

import fnmatch
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.application.ports.cache import Cache


@dataclass(frozen=True)
class CurrentUser:
    """Represents the currently authenticated user.

    This is a framework-agnostic user representation that can be
    populated from any authentication provider (JWT, OAuth, etc.)

    Immutable by design to prevent accidental modification and cache invalidation.

    Attributes:
        id: Unique user identifier
        permissions: Tuple of permission strings (e.g., "orders:read")
        roles: Tuple of role names (e.g., "admin", "user")
        metadata: Additional user data from the auth provider (frozen dict)

    Example:
        ```python
        user = CurrentUser(
            id="user-123",
            permissions=("orders:read", "orders:write"),
            roles=("admin",),
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
    permissions: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    _cache: "Cache | None" = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        """Validate permissions and roles after initialization."""
        # Validate permissions
        for perm in self.permissions:
            if not self._is_valid_permission(perm):
                raise ValueError(
                    f"Invalid permission format: '{perm}'. "
                    f"Permissions must be non-empty strings with max length 256."
                )

        # Validate roles
        for role in self.roles:
            if not self._is_valid_role(role):
                raise ValueError(
                    f"Invalid role format: '{role}'. "
                    f"Roles must be non-empty strings with max length 128."
                )

    def set_cache(self, cache: "Cache") -> None:
        """Set cache instance for permission checking.

        This allows using Bento's cache infrastructure for permission caching.

        Args:
            cache: Bento Cache instance

        Example:
            ```python
            from bento.adapters.cache import MemoryCache, CacheConfig

            cache = MemoryCache(CacheConfig(max_size=1000, ttl=3600))
            await cache.initialize()

            user = CurrentUser(id="user-1", permissions=("orders:*",))
            user.set_cache(cache)
            ```
        """
        object.__setattr__(self, '_cache', cache)

    @staticmethod
    def _is_valid_permission(perm: str) -> bool:
        """Validate permission format.

        Args:
            perm: Permission string to validate

        Returns:
            True if valid, False otherwise
        """
        return (
            isinstance(perm, str) and
            len(perm) > 0 and
            len(perm) <= 256 and
            not perm.isspace()
        )

    @staticmethod
    def _is_valid_role(role: str) -> bool:
        """Validate role format.

        Args:
            role: Role string to validate

        Returns:
            True if valid, False otherwise
        """
        return (
            isinstance(role, str) and
            len(role) > 0 and
            len(role) <= 128 and
            not role.isspace()
        )

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Supports wildcard patterns using fnmatch syntax:
        - "orders:*" matches "orders:read", "orders:write", etc.
        - "*:read" matches "orders:read", "products:read", etc.
        - "*" matches all permissions

        Uses Bento's cache infrastructure if configured for optimal performance.

        Args:
            permission: Permission string to check (supports wildcards)

        Returns:
            True if user has the permission (exact match or wildcard match)

        Example:
            ```python
            user = CurrentUser(
                id="user-1",
                permissions=("orders:*", "products:read"),
            )
            user.has_permission("orders:write")  # True (matches "orders:*")
            user.has_permission("products:read")  # True (exact match)
            user.has_permission("products:write")  # False
            ```
        """
        # Check exact match first (fast path)
        if permission in self.permissions:
            return True

        # Check wildcard patterns in user's permissions
        for perm in self.permissions:
            if fnmatch.fnmatch(permission, perm):
                return True

        return False

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the specified permissions.

        Supports wildcard patterns in user's permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has at least one of the permissions

        Example:
            ```python
            user = CurrentUser(
                id="user-1",
                permissions=["orders:*"],
            )
            user.has_any_permission(["orders:read", "products:write"])  # True
            ```
        """
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: list[str]) -> bool:
        """Check if user has all of the specified permissions.

        Supports wildcard patterns in user's permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has all of the permissions

        Example:
            ```python
            user = CurrentUser(
                id="user-1",
                permissions=["orders:*", "products:*"],
            )
            user.has_all_permissions(["orders:read", "products:write"])  # True
            ```
        """
        return all(self.has_permission(p) for p in permissions)

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
