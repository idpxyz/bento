"""Security context for Bento Framework.

This module provides request-scoped security context using ContextVar.

Example:
    ```python
    from bento.security import SecurityContext, CurrentUser

    # Set user (usually in middleware)
    user = CurrentUser(id="user-123", permissions=["read"])
    SecurityContext.set_user(user)

    # Get user (in business code)
    user = SecurityContext.get_user()  # May be None
    user = SecurityContext.require_user()  # Raises if None
    ```
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

from bento.core.exceptions import DomainException

if TYPE_CHECKING:
    from bento.security.models import CurrentUser


class SecurityContext:
    """Security context - stores current request's authenticated user and tenant.

    Uses ContextVar for async-safe, request-scoped storage.

    Example:
        ```python
        from bento.security import SecurityContext, CurrentUser

        # Set user and tenant (usually in middleware)
        user = CurrentUser(id="user-123", permissions=["orders:read"])
        SecurityContext.set_user(user)
        SecurityContext.set_tenant("tenant-456")

        # Get user (in business code)
        user = SecurityContext.get_user()  # May be None
        user = SecurityContext.require_user()  # Raises UNAUTHORIZED if None

        # Get tenant
        tenant_id = SecurityContext.get_tenant()  # May be None
        tenant_id = SecurityContext.require_tenant()  # Raises if None

        # Check permissions via context
        if SecurityContext.has_permission("orders:read"):
            ...
        ```
    """

    _current_user: ContextVar[CurrentUser | None] = ContextVar(
        'current_user', default=None
    )
    _current_tenant: ContextVar[str | None] = ContextVar(
        'current_tenant', default=None
    )

    @classmethod
    def get_user(cls) -> CurrentUser | None:
        """Get current authenticated user.

        Returns:
            Current user or None if not authenticated
        """
        return cls._current_user.get()

    @classmethod
    def require_user(cls) -> CurrentUser:
        """Get current user, raising if not authenticated.

        Returns:
            Current user

        Raises:
            DomainException: If not authenticated (UNAUTHORIZED)
        """
        user = cls._current_user.get()
        if not user:
            raise DomainException(reason_code="UNAUTHORIZED")
        return user

    @classmethod
    def set_user(cls, user: CurrentUser | None) -> None:
        """Set current authenticated user.

        Args:
            user: User to set, or None to clear
        """
        cls._current_user.set(user)

    @classmethod
    def clear(cls) -> None:
        """Clear current user and tenant.

        This clears both the authenticated user and tenant context.
        Use clear_user() or clear_tenant() if you need to clear only one.
        """
        cls._current_user.set(None)
        cls._current_tenant.set(None)

    @classmethod
    def clear_user(cls) -> None:
        """Clear only current user, keeping tenant."""
        cls._current_user.set(None)

    @classmethod
    def clear_tenant(cls) -> None:
        """Clear only current tenant, keeping user."""
        cls._current_tenant.set(None)

    @classmethod
    def is_authenticated(cls) -> bool:
        """Check if a user is currently authenticated.

        Returns:
            True if authenticated
        """
        return cls._current_user.get() is not None

    @classmethod
    def has_permission(cls, permission: str) -> bool:
        """Check if current user has a permission.

        Args:
            permission: Permission to check

        Returns:
            True if authenticated and has permission
        """
        user = cls._current_user.get()
        if not user:
            return False
        return user.has_permission(permission)

    @classmethod
    def has_role(cls, role: str) -> bool:
        """Check if current user has a role.

        Args:
            role: Role to check

        Returns:
            True if authenticated and has role
        """
        user = cls._current_user.get()
        if not user:
            return False
        return user.has_role(role)

    # Tenant methods
    @classmethod
    def get_tenant(cls) -> str | None:
        """Get current tenant ID.

        Returns:
            Current tenant ID or None if not set
        """
        return cls._current_tenant.get()

    @classmethod
    def require_tenant(cls) -> str:
        """Get current tenant ID, raising if not set.

        Returns:
            Current tenant ID

        Raises:
            DomainException: If tenant not set (TENANT_REQUIRED)
        """
        tenant_id = cls._current_tenant.get()
        if not tenant_id:
            raise DomainException(reason_code="TENANT_REQUIRED")
        return tenant_id

    @classmethod
    def set_tenant(cls, tenant_id: str | None) -> None:
        """Set current tenant ID.

        Args:
            tenant_id: Tenant ID to set, or None to clear
        """
        cls._current_tenant.set(tenant_id)
