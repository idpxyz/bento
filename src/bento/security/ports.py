"""Security ports (interfaces) for Bento Framework.

This module provides abstract interfaces for authentication and authorization
that applications must implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from fastapi import Request

    from bento.security.models import CurrentUser


class IAuthenticator(Protocol):
    """Protocol for authentication providers."""

    async def authenticate(self, request: Request) -> CurrentUser | None:
        """Authenticate a request and return the current user.

        Args:
            request: FastAPI request object

        Returns:
            CurrentUser if authenticated, None otherwise
        """
        ...


class IAuthorizer(Protocol):
    """Protocol for resource-based authorization.

    Allows checking if a user can perform an action on a specific resource.

    Example:
        ```python
        class OrderAuthorizer:
            async def authorize(
                self,
                user: CurrentUser,
                action: str,
                resource: Order,
            ) -> bool:
                # Admin can do anything
                if user.has_role("admin"):
                    return True

                # Users can only access their own orders
                if action in ["read", "update", "delete"]:
                    return resource.user_id == user.id

                return False
        ```
    """

    async def authorize(
        self,
        user: CurrentUser,
        action: str,
        resource: Any,
    ) -> bool:
        """Check if user is authorized to perform action on resource.

        Args:
            user: Current authenticated user
            action: Action to perform (e.g., "read", "write", "delete")
            resource: Resource to operate on

        Returns:
            True if authorized, False otherwise
        """
        ...
