"""Bento Multi-Tenancy module.

Provides tenant context management, resolution strategies, and middleware
for multi-tenant applications.

Example:
    ```python
    from fastapi import FastAPI
    from bento.multitenancy import (
        TenantContext,
        add_tenant_middleware,
        HeaderTenantResolver,
    )

    app = FastAPI()

    # Add tenant middleware
    add_tenant_middleware(
        app,
        resolver=HeaderTenantResolver(),
        require_tenant=True,
    )

    # In business code
    tenant_id = TenantContext.require()
    ```
"""

from bento.multitenancy.context import TenantContext
from bento.multitenancy.middleware import add_tenant_middleware
from bento.multitenancy.resolvers import (
    CompositeTenantResolver,
    HeaderTenantResolver,
    SubdomainTenantResolver,
    TenantResolver,
    TokenTenantResolver,
)

__all__ = [
    # Context
    "TenantContext",
    # Middleware
    "add_tenant_middleware",
    # Resolvers
    "TenantResolver",
    "HeaderTenantResolver",
    "TokenTenantResolver",
    "SubdomainTenantResolver",
    "CompositeTenantResolver",
]
