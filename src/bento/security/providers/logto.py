"""Logto authenticator for Bento Framework.

Logto is an open-source identity solution.
https://logto.io

Example:
    ```python
    from bento.security.providers import LogtoAuthenticator

    authenticator = LogtoAuthenticator(
        endpoint="https://your-app.logto.app",
        app_id="your-app-id",
    )

    add_security_middleware(app, authenticator)
    ```
"""

from __future__ import annotations

from bento.security.models import CurrentUser
from bento.security.providers.base import JWTAuthenticatorBase, JWTConfig


class LogtoAuthenticator(JWTAuthenticatorBase):
    """Authenticator for Logto identity provider.

    Logto uses OIDC-compliant JWT tokens with JWKS for verification.

    Attributes:
        endpoint: Logto endpoint URL (e.g., "https://your-app.logto.app")
        app_id: Logto application ID

    Example:
        ```python
        authenticator = LogtoAuthenticator(
            endpoint="https://your-app.logto.app",
            app_id="your-app-id",
        )

        # With custom claim mapping
        authenticator = LogtoAuthenticator(
            endpoint="https://your-app.logto.app",
            app_id="your-app-id",
            permissions_claim="permissions",
            roles_claim="roles",
        )
        ```
    """

    def __init__(
        self,
        endpoint: str,
        app_id: str,
        permissions_claim: str = "permissions",
        roles_claim: str = "roles",
    ):
        """Initialize Logto authenticator.

        Args:
            endpoint: Logto endpoint URL
            app_id: Logto application ID (used as audience)
            permissions_claim: Claim name for permissions
            roles_claim: Claim name for roles
        """
        self.endpoint = endpoint.rstrip("/")
        self.app_id = app_id
        self.permissions_claim = permissions_claim
        self.roles_claim = roles_claim

        config = JWTConfig(
            jwks_url=f"{self.endpoint}/oidc/.well-known/jwks.json",
            issuer=f"{self.endpoint}/oidc",
            audience=app_id,
        )
        super().__init__(config)

    def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
        """Extract CurrentUser from Logto token claims.

        Logto token structure:
        - sub: User ID
        - permissions: List of permission strings (if configured)
        - roles: List of role names (if configured)

        Args:
            claims: Verified JWT claims

        Returns:
            CurrentUser instance
        """
        return CurrentUser(
            id=claims["sub"],
            permissions=claims.get(self.permissions_claim, []),
            roles=claims.get(self.roles_claim, []),
            metadata={
                "email": claims.get("email"),
                "name": claims.get("name"),
                "picture": claims.get("picture"),
                "tenant_id": claims.get("tenant_id"),
            },
        )
