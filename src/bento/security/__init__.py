"""Bento Security module.

Provides security context, tenant management, and authentication utilities.

Example:
    ```python
    from bento.security import TenantContext, SecurityContext

    # Get current tenant
    tenant_id = TenantContext.require()

    # Get current user
    user = SecurityContext.get_current_user()
    ```
"""

from bento.security.tenant import (
    TenantContext,
    TenantResolver,
    HeaderTenantResolver,
    TokenTenantResolver,
    SubdomainTenantResolver,
    CompositeTenantResolver,
)
from bento.security.middleware import add_tenant_middleware

__all__ = [
    # Tenant Context
    "TenantContext",
    # Tenant Resolvers
    "TenantResolver",
    "HeaderTenantResolver",
    "TokenTenantResolver",
    "SubdomainTenantResolver",
    "CompositeTenantResolver",
    # Middleware
    "add_tenant_middleware",
]
