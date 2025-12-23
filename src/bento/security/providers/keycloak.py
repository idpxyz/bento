"""Keycloak authenticator for Bento Framework.

Keycloak is an open-source identity and access management solution.
https://keycloak.org

Example:
    ```python
    from bento.security.providers import KeycloakAuthenticator

    authenticator = KeycloakAuthenticator(
        server_url="https://keycloak.example.com",
        realm="your-realm",
        client_id="your-client-id",
    )

    add_security_middleware(app, authenticator)
    ```
"""

from __future__ import annotations

from bento.security.models import CurrentUser
from bento.security.providers.base import JWTAuthenticatorBase, JWTConfig


class KeycloakAuthenticator(JWTAuthenticatorBase):
    """Authenticator for Keycloak identity server.

    Keycloak uses OIDC-compliant JWT tokens with JWKS for verification.

    Attributes:
        server_url: Keycloak server URL
        realm: Keycloak realm name
        client_id: Client ID (used as audience)

    Example:
        ```python
        authenticator = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="your-realm",
            client_id="your-client-id",
        )

        # With realm roles extraction
        authenticator = KeycloakAuthenticator(
            server_url="https://keycloak.example.com",
            realm="your-realm",
            client_id="your-client-id",
            use_realm_roles=True,
        )
        ```
    """

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        use_realm_roles: bool = True,
        use_client_roles: bool = True,
    ):
        """Initialize Keycloak authenticator.

        Args:
            server_url: Keycloak server URL
            realm: Realm name
            client_id: Client ID
            use_realm_roles: Extract roles from realm_access
            use_client_roles: Extract roles from resource_access
        """
        self.server_url = server_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.use_realm_roles = use_realm_roles
        self.use_client_roles = use_client_roles

        realm_url = f"{self.server_url}/realms/{realm}"

        config = JWTConfig(
            jwks_url=f"{realm_url}/protocol/openid-connect/certs",
            issuer=realm_url,
            audience=client_id,
        )
        super().__init__(config)

    def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
        """Extract CurrentUser from Keycloak token claims.

        Keycloak token structure:
        - sub: User ID (UUID)
        - preferred_username: Username
        - realm_access.roles: Realm-level roles
        - resource_access.{client_id}.roles: Client-level roles

        Args:
            claims: Verified JWT claims

        Returns:
            CurrentUser instance
        """
        roles: list[str] = []

        # Extract realm roles
        if self.use_realm_roles:
            realm_access = claims.get("realm_access", {})
            roles.extend(realm_access.get("roles", []))

        # Extract client roles
        if self.use_client_roles:
            resource_access = claims.get("resource_access", {})
            client_access = resource_access.get(self.client_id, {})
            roles.extend(client_access.get("roles", []))

        # Keycloak can include scopes as permissions
        scope = claims.get("scope", "")
        permissions = scope.split() if isinstance(scope, str) else []

        return CurrentUser(
            id=claims["sub"],
            permissions=permissions,
            roles=roles,
            metadata={
                "email": claims.get("email"),
                "name": claims.get("name"),
                "preferred_username": claims.get("preferred_username"),
                "given_name": claims.get("given_name"),
                "family_name": claims.get("family_name"),
                "tenant_id": claims.get("tenant_id"),
                # Keycloak specific
                "azp": claims.get("azp"),  # Authorized party
                "session_state": claims.get("session_state"),
            },
        )
