"""M2M (Machine-to-Machine) authentication support.

This module provides M2M authentication using OAuth 2.0 Client Credentials Grant.

Example:
    ```python
    from bento.security.providers import LogtoAuthenticator

    # Enable M2M support by providing client credentials
    authenticator = LogtoAuthenticator(
        endpoint="https://your-app.logto.app",
        app_id="your-app-id",
        # M2M configuration
        client_id="m2m-client-id",
        client_secret="m2m-client-secret",
    )
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bento.security.models import CurrentUser


@dataclass
class M2MConfig:
    """Configuration for M2M authentication.

    Attributes:
        token_url: OAuth token endpoint URL
        client_id: Client ID for M2M authentication
        client_secret: Client secret for M2M authentication
        default_permissions: Permissions granted to M2M clients
        default_roles: Roles granted to M2M clients
    """

    token_url: str
    client_id: str
    client_secret: str
    default_permissions: list[str] | None = None
    default_roles: list[str] | None = None


class M2MAuthMixin:
    """Mixin for M2M (Machine-to-Machine) authentication.

    This mixin adds M2M authentication support to authenticators.
    M2M authentication is used for service-to-service communication.

    Detection Methods:
    1. X-M2M-Auth: true header
    2. X-Client-ID + X-Client-Secret headers
    3. Basic auth with client credentials

    Example:
        ```python
        class MyAuthenticator(JWTAuthenticatorBase, M2MAuthMixin):
            def __init__(self, ..., client_id=None, client_secret=None):
                ...
                if client_id and client_secret:
                    self.m2m_config = M2MConfig(
                        token_url=f"{endpoint}/oauth/token",
                        client_id=client_id,
                        client_secret=client_secret,
                    )
                else:
                    self.m2m_config = None
        ```
    """

    m2m_config: M2MConfig | None = None

    def supports_m2m(self) -> bool:
        """Check if M2M authentication is enabled.

        Returns:
            True if M2M config is set
        """
        return self.m2m_config is not None

    def should_use_m2m_auth(self, request: Any) -> bool:
        """Check if request should use M2M authentication.

        Detection methods:
        1. X-M2M-Auth: true header
        2. X-Client-ID header present
        3. No Authorization header but has client credentials

        Args:
            request: FastAPI Request object

        Returns:
            True if M2M auth should be used
        """
        if not self.supports_m2m():
            return False

        headers = request.headers

        # Method 1: Explicit M2M flag
        if headers.get("X-M2M-Auth", "").lower() == "true":
            return True

        # Method 2: Client ID header
        if headers.get("X-Client-ID"):
            return True

        # Method 3: Basic auth (could be client credentials)
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            return True

        return False

    async def authenticate_m2m(self, request: Any) -> CurrentUser | None:
        """Authenticate M2M request.

        Supports multiple authentication methods:
        1. X-Client-ID + X-Client-Secret headers
        2. Basic auth with client credentials
        3. Pre-configured client credentials (validates request origin)

        Args:
            request: FastAPI Request object

        Returns:
            CurrentUser for M2M client, or None if auth fails
        """
        if not self.m2m_config:
            return None

        client_id, client_secret = self._extract_client_credentials(request)

        # Validate credentials
        if not self._validate_client_credentials(client_id, client_secret):
            return None

        # Create M2M user
        return self._create_m2m_user(client_id)

    def _extract_client_credentials(
        self,
        request: Any,
    ) -> tuple[str | None, str | None]:
        """Extract client credentials from request.

        Args:
            request: FastAPI Request object

        Returns:
            Tuple of (client_id, client_secret)
        """
        headers = request.headers

        # Method 1: Custom headers
        client_id = headers.get("X-Client-ID")
        client_secret = headers.get("X-Client-Secret")
        if client_id and client_secret:
            return client_id, client_secret

        # Method 2: Basic auth
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                import base64
                credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
                if ":" in credentials:
                    client_id, client_secret = credentials.split(":", 1)
                    return client_id, client_secret
            except Exception:
                pass

        return None, None

    def _validate_client_credentials(
        self,
        client_id: str | None,
        client_secret: str | None,
    ) -> bool:
        """Validate client credentials.

        Args:
            client_id: Client ID to validate
            client_secret: Client secret to validate

        Returns:
            True if credentials are valid
        """
        if not self.m2m_config:
            return False

        return (
            client_id == self.m2m_config.client_id
            and client_secret == self.m2m_config.client_secret
        )

    def _create_m2m_user(self, client_id: str) -> CurrentUser:
        """Create CurrentUser for M2M client.

        Args:
            client_id: The authenticated client ID

        Returns:
            CurrentUser representing the M2M client
        """
        config = self.m2m_config
        return CurrentUser(
            id=f"m2m:{client_id}",
            permissions=config.default_permissions or [],
            roles=config.default_roles or [],
            metadata={
                "type": "m2m",
                "client_id": client_id,
            },
        )

    async def get_m2m_token(self, scope: str | None = None) -> str | None:
        """Get an access token using Client Credentials Grant.

        This is used when THIS service needs to call another service.

        Args:
            scope: Optional scope for the token

        Returns:
            Access token or None if failed
        """
        if not self.m2m_config:
            return None

        try:
            import httpx
        except ImportError as err:
            raise ImportError(
                "httpx is required for M2M token requests. "
                "Install it with: pip install httpx"
            ) from err

        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.m2m_config.client_id,
                "client_secret": self.m2m_config.client_secret,
            }
            if scope:
                data["scope"] = scope

            try:
                response = await client.post(
                    self.m2m_config.token_url,
                    data=data,
                )
                response.raise_for_status()
                return response.json().get("access_token")
            except Exception:
                return None
