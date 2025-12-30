"""Stub tenant resolver for LOMS application.

This is a P0 stub implementation that will be replaced with real
tenant resolution (e.g., from JWT claims, database lookup) in the future.

The implementation follows Bento Framework's ITenantResolver interface,
making it easy to swap with any real resolver later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request


class StubTenantResolver:
    """Stub tenant resolver for development/testing.

    This resolver:
    - Extracts tenant ID from X-Tenant-ID header
    - Falls back to "demo-tenant" if not provided
    - Should be replaced with real tenant resolution in production

    Future replacements:
    - Extract from JWT token claims
    - Database lookup based on subdomain
    - API key to tenant mapping
    """

    async def resolve_tenant(self, request: Request) -> str | None:
        """Resolve tenant ID from request (stub implementation).

        Args:
            request: FastAPI request

        Returns:
            Tenant ID from header or default "demo-tenant"
        """
        # P0 stub: Extract from header with fallback
        # In production, this could:
        # 1. Extract from JWT token claims
        # 2. Lookup from database based on subdomain
        # 3. Map from API key
        # 4. Use organization ID from user profile

        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")

        if not tenant_id:
            # Fallback to demo tenant for development
            tenant_id = "demo-tenant"

        return tenant_id


# Example: How to extract tenant from JWT token
"""
import jwt

class JWTTenantResolver:
    def __init__(self, jwks_url: str):
        self.jwks_client = PyJWKClient(jwks_url)

    async def resolve_tenant(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, signing_key.key, algorithms=["RS256"])

            # Extract tenant from token claims
            return claims.get("tenant_id") or claims.get("org_id")
        except Exception:
            return None
"""

# Example: How to resolve tenant from subdomain
"""
class SubdomainTenantResolver:
    def __init__(self, tenant_service):
        self.tenant_service = tenant_service

    async def resolve_tenant(self, request: Request) -> str | None:
        # Extract subdomain from host header
        host = request.headers.get("Host", "")
        subdomain = host.split(".")[0]

        # Lookup tenant by subdomain
        tenant = await self.tenant_service.get_by_subdomain(subdomain)
        return tenant.id if tenant else None
"""
