"""Resource-based authorization utilities for Bento Framework.

Provides decorators and helpers for checking if a user can access a resource.

Example:
    ```python
    from bento.security import authorize_resource, SecurityContext

    @authorize_resource(
        resource_getter=lambda req: get_order(req.path_params["order_id"]),
        action="read",
    )
    async def get_order_endpoint(order_id: str):
        order = await get_order(order_id)
        return order
    ```
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from bento.core.exceptions import DomainException
from bento.security.context import SecurityContext

if TYPE_CHECKING:
    from bento.security.models import CurrentUser

logger = logging.getLogger(__name__)

# Audit logging configuration
AUDIT_LOG_ENABLED = os.getenv("BENTO_AUDIT_LOG_ENABLED", "true").lower() == "true"
AUDIT_LOG_SUCCESS = os.getenv("BENTO_AUDIT_LOG_SUCCESS", "false").lower() == "true"


class OwnershipAuthorizer:
    """Simple ownership-based authorizer.

    Checks if user owns the resource by comparing user.id with a configurable
    owner field on the resource.

    Example:
        ```python
        # Default: checks resource.owner_id
        authorizer = OwnershipAuthorizer()

        # Custom field: checks resource.user_id
        authorizer = OwnershipAuthorizer(owner_field="user_id")

        # Custom field: checks resource.created_by
        authorizer = OwnershipAuthorizer(owner_field="created_by")

        order = Order(id="123", owner_id="user-1")
        user = CurrentUser(id="user-1")

        # True - user owns the order
        await authorizer.authorize(user, "read", order)
        ```
    """

    def __init__(
        self,
        owner_field: str = "created_by",
        strict_type_check: bool = False,
    ) -> None:
        """Initialize with configurable owner field.

        Args:
            owner_field: Name of the field on the resource that contains the owner ID
                        (default: "created_by")
            strict_type_check: If True, use strict type checking (owner_id == user.id).
                             If False, use string comparison (str(owner_id) == str(user.id))
                             (default: False for backward compatibility)
        """
        self.owner_field = owner_field
        self.strict_type_check = strict_type_check

    async def authorize(
        self,
        user: CurrentUser,
        action: str,
        resource: Any,
    ) -> bool:
        """Check if user owns the resource.

        Args:
            user: Current user
            action: Action being performed (not used in ownership check)
            resource: Resource to check ownership of

        Returns:
            True if user.id == resource.<owner_field>, False otherwise
        """
        if not hasattr(resource, self.owner_field):
            return False

        owner_id = getattr(resource, self.owner_field)

        if self.strict_type_check:
            # Strict type checking
            return owner_id == user.id
        else:
            # Lenient comparison (convert to string)
            return str(owner_id) == str(user.id)


class AdminBypassAuthorizer:
    """Authorizer that allows admins to bypass checks.

    Admins (users with "admin" role) can perform any action.
    Other users are checked by the wrapped authorizer.

    Example:
        ```python
        base_authorizer = OwnershipAuthorizer()
        authorizer = AdminBypassAuthorizer(base_authorizer)

        # Admin can do anything
        admin = CurrentUser(id="admin-1", roles=["admin"])
        await authorizer.authorize(admin, "delete", order)  # True

        # Regular user needs to own the resource
        user = CurrentUser(id="user-1", roles=[])
        await authorizer.authorize(user, "delete", order)  # Depends on ownership
        ```
    """

    def __init__(self, base_authorizer: Any) -> None:
        """Initialize with a base authorizer.

        Args:
            base_authorizer: Authorizer to use for non-admin users
        """
        self.base_authorizer = base_authorizer

    async def authorize(
        self,
        user: CurrentUser,
        action: str,
        resource: Any,
    ) -> bool:
        """Check authorization with admin bypass.

        Args:
            user: Current user
            action: Action being performed
            resource: Resource to check

        Returns:
            True if user is admin or base authorizer allows
        """
        # Admins can do anything
        if user.has_role("admin"):
            return True

        # Check with base authorizer
        return await self.base_authorizer.authorize(user, action, resource)


async def check_resource_access(
    user: CurrentUser,
    action: str,
    resource: Any,
    authorizer: Any,
    audit: bool = True,
) -> None:
    """Check if user can access a resource.

    Raises FORBIDDEN if not authorized.
    Logs authorization decisions based on configuration.

    Performance optimization: Only logs denied access by default.
    Set BENTO_AUDIT_LOG_SUCCESS=true to log successful access.

    Args:
        user: Current user
        action: Action to perform (e.g., "read", "write", "delete")
        resource: Resource to access
        authorizer: Authorizer instance with authorize() method
        audit: Enable/disable audit logging for this check (default: True)

    Raises:
        DomainException: If not authorized (reason_code="FORBIDDEN")

    Environment Variables:
        BENTO_AUDIT_LOG_ENABLED: Enable/disable all audit logging (default: true)
        BENTO_AUDIT_LOG_SUCCESS: Log successful authorizations (default: false)
    """
    resource_type = type(resource).__name__
    resource_id = getattr(resource, "id", None)

    is_authorized = await authorizer.authorize(user, action, resource)

    # Optimized audit logging
    if audit and AUDIT_LOG_ENABLED:
        if not is_authorized:
            # Always log denied access at WARNING level
            logger.warning(
                f"Access denied: user={user.id} action={action} resource={resource_type}:{resource_id}",
                extra={
                    "user_id": user.id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "authorized": False,
                    "authorizer": type(authorizer).__name__,
                },
            )
        elif AUDIT_LOG_SUCCESS:
            # Only log successful access if explicitly enabled
            logger.info(
                f"Access granted: user={user.id} action={action} resource={resource_type}:{resource_id}",
                extra={
                    "user_id": user.id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "authorized": True,
                    "authorizer": type(authorizer).__name__,
                },
            )
        elif logger.isEnabledFor(logging.DEBUG):
            # Log at DEBUG level if logger is in debug mode
            logger.debug(
                f"Access granted: user={user.id} action={action} resource={resource_type}:{resource_id}"
            )

    if not is_authorized:
        raise DomainException(
            reason_code="FORBIDDEN",
            details={
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )


def authorize_resource(
    resource_getter: Callable[..., Coroutine[Any, Any, Any]],
    action: str,
    authorizer: Any | None = None,
    inject_resource: bool = True,
    resource_param_name: str = "resource",
) -> Callable:
    """Decorator for resource-based authorization.

    Checks if current user can perform an action on a resource.
    Avoids double-querying by injecting the resource into the function.

    Args:
        resource_getter: Async function that returns the resource
        action: Action to check (e.g., "read", "write", "delete")
        authorizer: Authorizer instance (defaults to OwnershipAuthorizer)
        inject_resource: If True, inject resource as kwarg to avoid re-querying
        resource_param_name: Name of the parameter to inject resource into (default: "resource")

    Example:
        ```python
        @authorize_resource(
            resource_getter=lambda order_id: get_order(order_id),
            action="read",
        )
        async def get_order_endpoint(order_id: str, resource=None):
            # resource is injected, no need to query again
            return resource
        ```

    Raises:
        DomainException: If not authorized (reason_code="FORBIDDEN")
    """
    if authorizer is None:
        authorizer = OwnershipAuthorizer()

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Get current user
            user = SecurityContext.require_user()

            # Get resource - try kwargs first, then args
            try:
                resource = await resource_getter(**kwargs)
            except TypeError:
                # Fallback to positional args if kwargs don't work
                resource = await resource_getter(*args, **kwargs)

            # Check authorization
            await check_resource_access(user, action, resource, authorizer)

            # Inject resource to avoid re-querying
            if inject_resource:
                kwargs[resource_param_name] = resource

            # Call original function with resource
            return await func(*args, **kwargs)

        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        wrapper.__qualname__ = func.__qualname__
        wrapper.__annotations__ = func.__annotations__

        return wrapper

    return decorator
