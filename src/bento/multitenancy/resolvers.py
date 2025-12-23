"""Tenant resolution strategies for multi-tenant applications.

This module provides various strategies for resolving tenant ID from requests.

Example:
    ```python
    from bento.multitenancy import HeaderTenantResolver, TokenTenantResolver

    # From header
    resolver = HeaderTenantResolver(header_name="X-Tenant-ID")

    # From JWT token
    resolver = TokenTenantResolver(claim_name="tenant_id")
    ```
"""

from __future__ import annotations

from typing import Protocol, Any


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
