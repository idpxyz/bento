"""FastAPI middleware for multi-tenant support.

This module provides middleware for automatic tenant context setup
in FastAPI applications.

Example:
    ```python
    from fastapi import FastAPI
    from bento.multitenancy import add_tenant_middleware, HeaderTenantResolver

    app = FastAPI()
    add_tenant_middleware(
        app,
        resolver=HeaderTenantResolver(),
        require_tenant=True,
    )
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from bento.multitenancy.context import TenantContext
from bento.multitenancy.resolvers import TenantResolver


def add_tenant_middleware(
    app: "FastAPI",
    resolver: TenantResolver,
    require_tenant: bool = False,
    exclude_paths: list[str] | None = None,
    sync_to_security_context: bool = True,
) -> None:
    """Add tenant middleware to FastAPI application.

    This middleware:
    1. Resolves tenant ID using the provided resolver
    2. Sets TenantContext for the request duration
    3. Optionally syncs to SecurityContext for business logic access
    4. Optionally requires tenant for all requests

    Args:
        app: FastAPI application instance
        resolver: TenantResolver implementation
        require_tenant: If True, return 400 when tenant is missing
        exclude_paths: Paths to exclude from tenant requirement
                      (e.g., ["/health", "/docs"])
        sync_to_security_context: If True, also set tenant in SecurityContext
                                 for downstream business logic access

    Example:
        ```python
        from fastapi import FastAPI
        from bento.multitenancy import add_tenant_middleware, TokenTenantResolver

        app = FastAPI()

        add_tenant_middleware(
            app,
            resolver=TokenTenantResolver(claim_name="tenant_id"),
            require_tenant=True,
            exclude_paths=["/health", "/docs", "/openapi.json"],
            sync_to_security_context=True,  # Auto-sync to SecurityContext
        )
        ```
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    exclude_paths = exclude_paths or []

    # Import SecurityContext only if sync is enabled
    security_context = None
    if sync_to_security_context:
        try:
            from bento.security import SecurityContext
            security_context = SecurityContext
        except ImportError:
            # SecurityContext not available, skip sync
            pass

    @app.middleware("http")
    async def tenant_middleware(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        call_next,
    ):
        # Check if path is excluded
        path = request.url.path
        if any(path.startswith(ep) for ep in exclude_paths):
            return await call_next(request)

        # Resolve tenant
        tenant_id = resolver.resolve(request)

        # Check if tenant is required
        if require_tenant and not tenant_id:
            return JSONResponse(
                status_code=400,
                content={
                    "reason_code": "TENANT_REQUIRED",
                    "message": "Tenant ID is required for this operation",
                    "category": "client",
                    "details": {},
                    "retryable": False,
                },
            )

        # Set tenant context
        TenantContext.set(tenant_id)

        # Optionally sync to SecurityContext for business logic access
        if security_context:
            security_context.set_tenant(tenant_id)

        try:
            response = await call_next(request)
            return response
        finally:
            # Always clear contexts
            TenantContext.clear()
            if security_context:
                security_context.set_tenant(None)
