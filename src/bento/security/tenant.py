"""Multi-tenant support for Bento Framework.

This module provides tenant context management and resolution strategies
for multi-tenant applications.

Example:
    ```python
    from fastapi import FastAPI
    from bento.security.tenant import (
        TenantContext,
        TokenTenantResolver,
        add_tenant_middleware,
    )

    app = FastAPI()

    # Add tenant middleware
    add_tenant_middleware(
        app,
        resolver=TokenTenantResolver(),
        require_tenant=True,
    )

    # In business code
    tenant_id = TenantContext.require()  # Raises if no tenant
    ```
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Protocol, Any

from bento.core.exceptions import DomainException


class TenantContext:
    """Tenant context - stores current request's tenant information.

    Uses ContextVar for async-safe, request-scoped tenant storage.

    Example:
        ```python
        # Set tenant (usually in middleware)
        TenantContext.set("tenant-123")

        # Get tenant (in business code)
        tenant_id = TenantContext.get()  # May be None
        tenant_id = TenantContext.require()  # Raises if None
        ```
    """

    _current_tenant: ContextVar[str | None] = ContextVar(
        'current_tenant', default=None
    )

    @classmethod
    def get(cls) -> str | None:
        """Get current tenant ID.

        Returns:
            Current tenant ID or None if not set
        """
        return cls._current_tenant.get()

    @classmethod
    def require(cls) -> str:
        """Get current tenant ID, raising if not set.

        Returns:
            Current tenant ID

        Raises:
            DomainException: If tenant is not set (TENANT_REQUIRED)
        """
        tenant_id = cls._current_tenant.get()
        if not tenant_id:
            raise DomainException(reason_code="TENANT_REQUIRED")
        return tenant_id

    @classmethod
    def set(cls, tenant_id: str | None) -> None:
        """Set current tenant ID.

        Args:
            tenant_id: Tenant ID to set, or None to clear
        """
        cls._current_tenant.set(tenant_id)

    @classmethod
    def clear(cls) -> None:
        """Clear current tenant."""
        cls._current_tenant.set(None)


class TenantResolver(Protocol):
    """Protocol for tenant resolution strategies.

    Implementations determine how to extract tenant ID from requests.
    Common strategies include:
    - Header-based (X-Tenant-ID)
    - Token-based (JWT claim)
    - Subdomain-based (tenant.example.com)
    """

    def resolve(self, request: Any) -> str | None:
        """Resolve tenant ID from request.

        Args:
            request: The incoming request (e.g., FastAPI Request)

        Returns:
            Resolved tenant ID or None
        """
        ...


class HeaderTenantResolver:
    """Resolve tenant from HTTP header.

    Example:
        ```python
        resolver = HeaderTenantResolver(header_name="X-Tenant-ID")
        # Request with header "X-Tenant-ID: tenant-123"
        # resolver.resolve(request) -> "tenant-123"
        ```
    """

    def __init__(self, header_name: str = "X-Tenant-ID"):
        """Initialize resolver.

        Args:
            header_name: Name of the header containing tenant ID
        """
        self.header_name = header_name

    def resolve(self, request: Any) -> str | None:
        """Resolve tenant from request header.

        Args:
            request: FastAPI Request object

        Returns:
            Tenant ID from header or None
        """
        return request.headers.get(self.header_name)


class TokenTenantResolver:
    """Resolve tenant from JWT token claims.

    Requires SecurityContext to be set up first (user must be authenticated).

    Example:
        ```python
        resolver = TokenTenantResolver(claim_name="tenant_id")
        # Token with claim {"tenant_id": "tenant-123"}
        # resolver.resolve(request) -> "tenant-123"
        ```
    """

    def __init__(self, claim_name: str = "tenant_id"):
        """Initialize resolver.

        Args:
            claim_name: Name of the JWT claim containing tenant ID
        """
        self.claim_name = claim_name

    def resolve(self, request: Any) -> str | None:
        """Resolve tenant from user's token claims.

        Args:
            request: FastAPI Request object (not directly used)

        Returns:
            Tenant ID from token or None
        """
        try:
            from bento.security.context import SecurityContext
            user = SecurityContext.get_current_user()
            if user and user.metadata:
                return user.metadata.get(self.claim_name)
        except ImportError:
            pass
        return None


class SubdomainTenantResolver:
    """Resolve tenant from subdomain.

    Example:
        ```python
        resolver = SubdomainTenantResolver()
        # Request to "acme.example.com"
        # resolver.resolve(request) -> "acme"
        ```
    """

    def __init__(self, min_parts: int = 3):
        """Initialize resolver.

        Args:
            min_parts: Minimum number of domain parts to consider subdomain
                       (e.g., 3 for "tenant.example.com")
        """
        self.min_parts = min_parts

    def resolve(self, request: Any) -> str | None:
        """Resolve tenant from subdomain.

        Args:
            request: FastAPI Request object

        Returns:
            Subdomain as tenant ID or None
        """
        host = request.headers.get("host", "")
        # Remove port if present
        host = host.split(":")[0]
        parts = host.split(".")
        if len(parts) >= self.min_parts:
            return parts[0]
        return None


class CompositeTenantResolver:
    """Try multiple resolvers in order.

    Example:
        ```python
        resolver = CompositeTenantResolver([
            HeaderTenantResolver(),
            TokenTenantResolver(),
        ])
        # Tries header first, then token
        ```
    """

    def __init__(self, resolvers: list[TenantResolver]):
        """Initialize with list of resolvers.

        Args:
            resolvers: Resolvers to try in order
        """
        self.resolvers = resolvers

    def resolve(self, request: Any) -> str | None:
        """Try each resolver until one returns a value.

        Args:
            request: FastAPI Request object

        Returns:
            First non-None tenant ID or None
        """
        for resolver in self.resolvers:
            tenant_id = resolver.resolve(request)
            if tenant_id:
                return tenant_id
        return None
