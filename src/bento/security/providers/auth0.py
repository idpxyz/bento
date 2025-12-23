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

from bento.security.models import CurrentUser
from bento.security.providers.base import JWTAuthenticatorBase, JWTConfig


class Auth0Authenticator(JWTAuthenticatorBase):
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
    ):
        """Initialize Auth0 authenticator.

        Args:
            domain: Auth0 tenant domain
            audience: API audience identifier
            namespace: Custom namespace for claims (Auth0 requires namespaced claims)
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
