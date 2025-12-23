"""Security ports (interfaces) for Bento Framework.

This module provides abstract interfaces for authentication and authorization
that applications must implement.

Example:
    ```python
    from bento.security.ports import IAuthenticator
    from bento.security import CurrentUser

    class JWTAuthenticator(IAuthenticator):
        async def authenticate(self, request):
            token = request.headers.get("Authorization")
            if not token:
                return None
            claims = await self.verify_jwt(token)
            return CurrentUser(
                id=claims["sub"],
                permissions=claims.get("permissions", []),
            )
    ```
"""

from __future__ import annotations

from typing import Protocol, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from bento.security.models import CurrentUser


class IAuthenticator(Protocol):
    """Protocol for authentication providers.

    Applications implement this interface to provide authentication logic.
    The framework calls `authenticate()` for each request.

    Example:
        ```python
        class JWTAuthenticator(IAuthenticator):
            def __init__(self, jwks_url: str, audience: str):
                self.jwks_url = jwks_url
                self.audience = audience

            async def authenticate(self, request) -> CurrentUser | None:
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return None

                token = auth_header[7:]
                claims = await self._verify_token(token)

                return CurrentUser(
                    id=claims["sub"],
                    permissions=claims.get("permissions", []),
                    roles=claims.get("roles", []),
                    metadata=claims,
                )
        ```
    """

    async def authenticate(self, request: Any) -> "CurrentUser | None":
        """Authenticate a request and return the current user.

        Args:
            request: The incoming request (e.g., FastAPI Request)

        Returns:
            CurrentUser if authenticated, None otherwise
        """
        ...


class IAuthorizer(Protocol):
    """Protocol for authorization providers.

    Applications can implement this interface for custom authorization logic
    beyond simple permission/role checks.

    Example:
        ```python
        class ResourceAuthorizer(IAuthorizer):
            async def authorize(self, user, permission, resource=None):
                # Check if user owns the resource
                if resource and hasattr(resource, 'owner_id'):
                    if resource.owner_id == user.id:
                        return True

                # Fall back to permission check
                return user.has_permission(permission)
        ```
    """

    async def authorize(
        self,
        user: "CurrentUser",
        permission: str,
        resource: Any = None,
    ) -> bool:
        """Check if user is authorized for an action.

        Args:
            user: The authenticated user
            permission: Permission string to check
            resource: Optional resource for resource-based authorization

        Returns:
            True if authorized
        """
        ...
