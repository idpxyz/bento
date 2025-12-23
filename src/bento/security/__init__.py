"""Bento Security module.

Provides authentication and authorization utilities for Bento applications.

Note: Multi-tenant support is in `bento.multitenancy` module.

Example:
    ```python
    from fastapi import FastAPI
    from bento.security import (
        SecurityContext,
        CurrentUser,
        add_security_middleware,
        IAuthenticator,
    )

    # Implement authenticator
    class MyAuthenticator(IAuthenticator):
        async def authenticate(self, request):
            # Your auth logic
            return CurrentUser(id="user-123", permissions=["read"])

    # Add middleware
    app = FastAPI()
    add_security_middleware(app, MyAuthenticator())

    # In business code
    user = SecurityContext.require_user()
    ```
"""

from bento.security.context import SecurityContext
from bento.security.models import CurrentUser
from bento.security.ports import IAuthenticator, IAuthorizer
from bento.security.middleware import add_security_middleware
from bento.security.decorators import (
    require_auth,
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    require_any_role,
    require_all_roles,
    require_owner_or_role,
)
from bento.security.depends import (
    get_current_user,
    get_optional_user,
    require_permissions,
    require_roles,
)

__all__ = [
    # Context
    "SecurityContext",
    # Models
    "CurrentUser",
    # Ports (interfaces)
    "IAuthenticator",
    "IAuthorizer",
    # Middleware
    "add_security_middleware",
    # Decorators
    "require_auth",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "require_owner_or_role",
    # FastAPI Depends
    "get_current_user",
    "get_optional_user",
    "require_permissions",
    "require_roles",
]

