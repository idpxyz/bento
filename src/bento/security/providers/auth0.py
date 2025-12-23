"""Auth0 authenticator for Bento Framework.

Auth0 is a popular identity platform.
https://auth0.com

Example:
    ```python
    from bento.security.providers import Auth0Authenticator

    authenticator = Auth0Authenticator(
        domain="your-tenant.auth0.com",
        audience="https://your-api.example.com",
    )

    add_security_middleware(app, authenticator)
    ```
"""

from __future__ import annotations

from typing import Any

from bento.security.models import CurrentUser
from bento.security.providers.base import JWTAuthenticatorBase, JWTConfig
from bento.security.providers.m2m import M2MAuthMixin, M2MConfig


class Auth0Authenticator(M2MAuthMixin, JWTAuthenticatorBase):
    """Authenticator for Auth0 identity platform.

    Auth0 uses OIDC-compliant JWT tokens with JWKS for verification.

    Attributes:
        domain: Auth0 tenant domain (e.g., "your-tenant.auth0.com")
        audience: API audience identifier

    Example:
        ```python
        authenticator = Auth0Authenticator(
            domain="your-tenant.auth0.com",
            audience="https://your-api.example.com",
        )

        # With custom namespace for permissions
        authenticator = Auth0Authenticator(
            domain="your-tenant.auth0.com",
            audience="https://your-api.example.com",
            namespace="https://your-app.com/",
        )
        ```
    """

    def __init__(
        self,
        domain: str,
        audience: str,
        namespace: str = "",
        # M2M configuration (optional)
        client_id: str | None = None,
        client_secret: str | None = None,
        m2m_permissions: list[str] | None = None,
        m2m_roles: list[str] | None = None,
    ):
        """Initialize Auth0 authenticator.

        Args:
            domain: Auth0 tenant domain
            audience: API audience identifier
            namespace: Custom namespace for claims (Auth0 requires namespaced claims)
            client_id: M2M client ID (enables M2M auth)
            client_secret: M2M client secret
            m2m_permissions: Default permissions for M2M clients
            m2m_roles: Default roles for M2M clients
        """
        self.domain = domain.rstrip("/")
        self.audience = audience
        self.namespace = namespace

        config = JWTConfig(
            jwks_url=f"https://{self.domain}/.well-known/jwks.json",
            issuer=f"https://{self.domain}/",
            audience=audience,
        )
        super().__init__(config)

        # Initialize M2M support
        if client_id and client_secret:
            self.m2m_config = M2MConfig(
                token_url=f"https://{self.domain}/oauth/token",
                client_id=client_id,
                client_secret=client_secret,
                default_permissions=m2m_permissions,
                default_roles=m2m_roles,
            )
        else:
            self.m2m_config = None

    async def authenticate(self, request: Any) -> CurrentUser | None:
        """Authenticate request (user or M2M).

        Args:
            request: FastAPI Request object

        Returns:
            CurrentUser if authenticated, None otherwise
        """
        if self.should_use_m2m_auth(request):
            return await self.authenticate_m2m(request)
        return await super().authenticate(request)

    def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
        """Extract CurrentUser from Auth0 token claims.

        Auth0 token structure:
        - sub: User ID (format: "auth0|user_id" or "provider|id")
        - {namespace}permissions: List of permissions (if using RBAC)
        - {namespace}roles: List of roles (if using RBAC)

        Args:
            claims: Verified JWT claims

        Returns:
            CurrentUser instance
        """
        # Auth0 uses namespaced claims for custom data
        permissions_key = f"{self.namespace}permissions"
        roles_key = f"{self.namespace}roles"

        # Also check standard 'permissions' claim (API permissions)
        permissions = claims.get(permissions_key, [])
        if not permissions:
            permissions = claims.get("permissions", [])

        return CurrentUser(
            id=claims["sub"],
            permissions=permissions,
            roles=claims.get(roles_key, []),
            metadata={
                "email": claims.get("email") or claims.get(f"{self.namespace}email"),
                "name": claims.get("name") or claims.get(f"{self.namespace}name"),
                "picture": claims.get("picture"),
                "tenant_id": claims.get(f"{self.namespace}tenant_id"),
                # Auth0 specific
                "azp": claims.get("azp"),  # Authorized party
                "scope": claims.get("scope"),  # Token scopes
            },
        )
