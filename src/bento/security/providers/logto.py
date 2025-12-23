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

from typing import Any

from bento.security.models import CurrentUser
from bento.security.providers.base import JWTAuthenticatorBase, JWTConfig
from bento.security.providers.m2m import M2MAuthMixin, M2MConfig  # noqa: F401


class LogtoAuthenticator(M2MAuthMixin, JWTAuthenticatorBase):
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
        # M2M configuration (optional)
        client_id: str | None = None,
        client_secret: str | None = None,
        m2m_permissions: list[str] | None = None,
        m2m_roles: list[str] | None = None,
    ):
        """Initialize Logto authenticator.

        Args:
            endpoint: Logto endpoint URL
            app_id: Logto application ID (used as audience)
            permissions_claim: Claim name for permissions
            roles_claim: Claim name for roles
            client_id: M2M client ID (enables M2M auth)
            client_secret: M2M client secret
            m2m_permissions: Default permissions for M2M clients
            m2m_roles: Default roles for M2M clients
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

        # Initialize M2M support
        if client_id and client_secret:
            self.m2m_config = M2MConfig(
                token_url=f"{self.endpoint}/oidc/token",
                client_id=client_id,
                client_secret=client_secret,
                default_permissions=m2m_permissions,
                default_roles=m2m_roles,
            )
        else:
            self.m2m_config = None

    async def authenticate(self, request: Any) -> CurrentUser | None:
        """Authenticate request (user or M2M).

        Checks for M2M auth first, then falls back to user JWT auth.

        Args:
            request: FastAPI Request object

        Returns:
            CurrentUser if authenticated, None otherwise
        """
        # Try M2M auth first
        if self.should_use_m2m_auth(request):
            return await self.authenticate_m2m(request)

        # Fall back to JWT auth
        return await super().authenticate(request)

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
