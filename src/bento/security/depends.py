"""FastAPI dependency injection for security.

This module provides FastAPI-style dependencies for authentication.

Example:
    ```python
    from fastapi import Depends
    from bento.security.depends import get_current_user, get_optional_user

    @app.get("/profile")
    async def get_profile(user: CurrentUser = Depends(get_current_user)):
        return {"id": user.id}

    @app.get("/public")
    async def public_endpoint(user: CurrentUser | None = Depends(get_optional_user)):
        if user:
            return {"message": f"Hello, {user.id}"}
        return {"message": "Hello, guest"}
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bento.core.exceptions import DomainException
from bento.security.context import SecurityContext

if TYPE_CHECKING:
    from bento.security.models import CurrentUser


async def get_current_user() -> CurrentUser:
    """FastAPI dependency that returns the current authenticated user.

    Raises:
        DomainException: UNAUTHORIZED if not authenticated

    Example:
        ```python
        from fastapi import Depends
        from bento.security.depends import get_current_user

        @app.get("/me")
        async def get_me(user: CurrentUser = Depends(get_current_user)):
            return {"id": user.id, "roles": user.roles}
        ```
    """
    user = SecurityContext.get_user()
    if not user:
        raise DomainException(reason_code="UNAUTHORIZED")
    return user


async def get_optional_user() -> CurrentUser | None:
    """FastAPI dependency that returns the current user or None.

    Does not raise if not authenticated.

    Example:
        ```python
        from fastapi import Depends
        from bento.security.depends import get_optional_user

        @app.get("/greeting")
        async def greeting(user: CurrentUser | None = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.id}"}
            return {"message": "Hello, guest"}
        ```
    """
    return SecurityContext.get_user()


def require_permissions(*permissions: str):
    """Factory for FastAPI dependency that requires specific permissions.

    Args:
        *permissions: Required permissions

    Example:
        ```python
        from fastapi import Depends
        from bento.security.depends import require_permissions

        @app.post("/orders")
        async def create_order(
            user: CurrentUser = Depends(require_permissions("orders:write"))
        ):
            ...
        ```
    """
    async def dependency() -> CurrentUser:
        user = await get_current_user()
        if not user.has_all_permissions(list(permissions)):
            raise DomainException(
                reason_code="FORBIDDEN",
                details={"required_permissions": list(permissions)},
            )
        return user
    return dependency


def require_roles(*roles: str):
    """Factory for FastAPI dependency that requires specific roles.

    Args:
        *roles: Required roles (user must have ALL)

    Example:
        ```python
        from fastapi import Depends
        from bento.security.depends import require_roles

        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            admin: CurrentUser = Depends(require_roles("admin"))
        ):
            ...
        ```
    """
    async def dependency() -> CurrentUser:
        user = await get_current_user()
        for role in roles:
            if not user.has_role(role):
                raise DomainException(
                    reason_code="FORBIDDEN",
                    details={"required_roles": list(roles)},
                )
        return user
    return dependency


def require_any_role(*roles: str):
    """Factory for FastAPI dependency that requires any of the roles.

    Args:
        *roles: Roles to check (user must have at least one)

    Example:
        ```python
        from fastapi import Depends
        from bento.security.depends import require_any_role

        @app.get("/moderation")
        async def moderation_panel(
            user: CurrentUser = Depends(require_any_role("admin", "moderator"))
        ):
            ...
        ```
    """
    async def dependency() -> CurrentUser:
        user = await get_current_user()
        if not user.has_any_role(list(roles)):
            raise DomainException(
                reason_code="FORBIDDEN",
                details={"required_roles": list(roles), "mode": "any"},
            )
        return user
    return dependency
