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
    """Security context - stores current request's authenticated user.

    Uses ContextVar for async-safe, request-scoped user storage.

    Example:
        ```python
        from bento.security import SecurityContext, CurrentUser

        # Set user (usually in middleware)
        user = CurrentUser(id="user-123", permissions=["orders:read"])
        SecurityContext.set_user(user)

        # Get user (in business code)
        user = SecurityContext.get_user()  # May be None
        user = SecurityContext.require_user()  # Raises UNAUTHORIZED if None

        # Check permissions via context
        if SecurityContext.has_permission("orders:read"):
            ...
        ```
    """

    _current_user: ContextVar["CurrentUser | None"] = ContextVar(
        'current_user', default=None
    )

    @classmethod
    def get_user(cls) -> "CurrentUser | None":
        """Get current authenticated user.

        Returns:
            Current user or None if not authenticated
        """
        return cls._current_user.get()

    @classmethod
    def require_user(cls) -> "CurrentUser":
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
    def set_user(cls, user: "CurrentUser | None") -> None:
        """Set current authenticated user.

        Args:
            user: User to set, or None to clear
        """
        cls._current_user.set(user)

    @classmethod
    def clear(cls) -> None:
        """Clear current user."""
        cls._current_user.set(None)

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
