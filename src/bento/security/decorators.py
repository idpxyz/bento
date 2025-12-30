"""Security decorators for Bento Framework.

This module provides decorators for declarative security checks.

Example:
    ```python
    from bento.security.decorators import require_auth, require_permission

    @require_auth
    async def protected_endpoint():
        ...

    @require_permission("orders:write")
    async def create_order():
        ...
    ```
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from bento.core.exceptions import DomainException
from bento.security.context import SecurityContext


def require_auth(func: Callable) -> Callable:
    """Decorator that requires authentication.

    Raises UNAUTHORIZED if no user is authenticated.

    Example:
        ```python
        @require_auth
        async def protected_endpoint():
            user = SecurityContext.get_user()  # Guaranteed to exist
            ...
        ```
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        SecurityContext.require_user()
        return await func(*args, **kwargs)
    return wrapper


def require_permission(permission: str) -> Callable:
    """Decorator that requires a specific permission.

    Raises UNAUTHORIZED if not authenticated.
    Raises FORBIDDEN if user lacks the permission.

    Args:
        permission: Permission string to check (e.g., "orders:write")

    Example:
        ```python
        @require_permission("orders:write")
        async def create_order():
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()
            if not user.has_permission(permission):
                raise DomainException(
                    reason_code="FORBIDDEN",
                    details={"required_permission": permission},
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: str) -> Callable:
    """Decorator that requires any of the specified permissions.

    Raises UNAUTHORIZED if not authenticated.
    Raises FORBIDDEN if user has none of the permissions.

    Args:
        *permissions: Permission strings to check

    Example:
        ```python
        @require_any_permission("orders:read", "orders:admin")
        async def view_order():
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()
            if not user.has_any_permission(list(permissions)):
                raise DomainException(
                    reason_code="FORBIDDEN",
                    details={"required_permissions": list(permissions), "mode": "any"},
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permissions: str) -> Callable:
    """Decorator that requires all of the specified permissions.

    Raises UNAUTHORIZED if not authenticated.
    Raises FORBIDDEN if user lacks any of the permissions.

    Args:
        *permissions: Permission strings to check

    Example:
        ```python
        @require_all_permissions("orders:read", "orders:write")
        async def manage_order():
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()
            if not user.has_all_permissions(list(permissions)):
                raise DomainException(
                    reason_code="FORBIDDEN",
                    details={"required_permissions": list(permissions), "mode": "all"},
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str) -> Callable:
    """Decorator that requires a specific role.

    Raises UNAUTHORIZED if not authenticated.
    Raises FORBIDDEN if user lacks the role.

    Args:
        role: Role name to check

    Example:
        ```python
        @require_role("admin")
        async def admin_only():
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()
            if not user.has_role(role):
                raise DomainException(
                    reason_code="FORBIDDEN",
                    details={"required_role": role},
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*roles: str) -> Callable:
    """Decorator that requires any of the specified roles.

    Raises UNAUTHORIZED if not authenticated.
    Raises FORBIDDEN if user has none of the roles.

    Args:
        *roles: Role names to check

    Example:
        ```python
        @require_any_role("admin", "moderator")
        async def moderation_action():
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()
            if not user.has_any_role(list(roles)):
                raise DomainException(
                    reason_code="FORBIDDEN",
                    details={"required_roles": list(roles), "mode": "any"},
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_roles(*roles: str) -> Callable:
    """Decorator that requires all of the specified roles.

    Raises UNAUTHORIZED if not authenticated.
    Raises FORBIDDEN if user lacks any of the roles.

    Args:
        *roles: Role names to check

    Example:
        ```python
        @require_all_roles("admin", "super_admin")
        async def super_admin_action():
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()
            for role in roles:
                if not user.has_role(role):
                    raise DomainException(
                        reason_code="FORBIDDEN",
                        details={"required_roles": list(roles), "mode": "all"},
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_owner_or_role(
    role: str,
    owner_getter: Callable[[Any], str] | None = None,
) -> Callable:
    """Decorator that requires ownership or a specific role.

    Useful for resource-based authorization where owners and admins
    can access a resource.

    Args:
        role: Role that bypasses ownership check (e.g., "admin")
        owner_getter: Function to extract owner_id from first argument.
                     If None, checks first arg for `owner_id` attribute.

    Example:
        ```python
        @require_owner_or_role("admin")
        async def update_order(order: Order):
            # order.owner_id must match user.id, or user must be admin
            ...

        @require_owner_or_role("admin", owner_getter=lambda o: o.created_by)
        async def delete_item(item: Item):
            ...
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = SecurityContext.require_user()

            # Admin bypass
            if user.has_role(role):
                return await func(*args, **kwargs)

            # Check ownership
            if args:
                resource = args[0]
                if owner_getter:
                    owner_id = owner_getter(resource)
                elif hasattr(resource, 'owner_id'):
                    owner_id = resource.owner_id
                else:
                    owner_id = None

                if owner_id and str(owner_id) == str(user.id):
                    return await func(*args, **kwargs)

            raise DomainException(
                reason_code="FORBIDDEN",
                details={"required": f"owner or {role}"},
            )
        return wrapper
    return decorator
