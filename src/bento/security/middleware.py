"""FastAPI middleware for multi-tenant support.

This module provides middleware for automatic tenant context setup
in FastAPI applications.

Example:
    ```python
    from fastapi import FastAPI
    from bento.security.middleware import add_tenant_middleware
    from bento.security.tenant import HeaderTenantResolver

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

from bento.security.tenant import TenantContext, TenantResolver


def add_tenant_middleware(
    app: "FastAPI",
    resolver: TenantResolver,
    require_tenant: bool = False,
    exclude_paths: list[str] | None = None,
) -> None:
    """Add tenant middleware to FastAPI application.

    This middleware:
    1. Resolves tenant ID using the provided resolver
    2. Sets TenantContext for the request duration
    3. Optionally requires tenant for all requests

    Args:
        app: FastAPI application instance
        resolver: TenantResolver implementation
        require_tenant: If True, return 400 when tenant is missing
        exclude_paths: Paths to exclude from tenant requirement
                      (e.g., ["/health", "/docs"])

    Example:
        ```python
        from fastapi import FastAPI
        from bento.security.middleware import add_tenant_middleware
        from bento.security.tenant import TokenTenantResolver

        app = FastAPI()

        add_tenant_middleware(
            app,
            resolver=TokenTenantResolver(claim_name="tenant_id"),
            require_tenant=True,
            exclude_paths=["/health", "/docs", "/openapi.json"],
        )
        ```
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    exclude_paths = exclude_paths or []

    @app.middleware("http")
    async def tenant_middleware(request: Request, call_next):
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

        try:
            response = await call_next(request)
            return response
        finally:
            # Always clear context
            TenantContext.clear()
