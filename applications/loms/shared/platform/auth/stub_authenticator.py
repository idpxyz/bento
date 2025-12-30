"""Stub authenticator for LOMS application.

This is a P0 stub implementation that will be replaced with real
authentication (e.g., bento-security, JWT, OAuth) in the future.

The implementation follows Bento Framework's IAuthenticator interface,
making it easy to swap with any real authenticator later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bento.security import CurrentUser

if TYPE_CHECKING:
    from fastapi import Request


class StubAuthenticator:
    """Stub authenticator for development/testing.

    This authenticator:
    - Accepts any request as authenticated
    - Creates a demo user with full permissions
    - Should be replaced with real auth in production

    Future replacements:
    - bento-security with Logto/Auth0
    - Custom JWT authenticator
    - OAuth2 provider
    """

    async def authenticate(self, request: Request) -> CurrentUser | None:
        """Authenticate request (stub implementation).

        Args:
            request: FastAPI request

        Returns:
            Demo user with full permissions
        """
        # P0 stub: Accept all requests as authenticated
        # In production, this would:
        # 1. Extract token from Authorization header
        # 2. Verify token (JWT, OAuth, etc.)
        # 3. Extract user claims
        # 4. Return CurrentUser with real permissions

        return CurrentUser(
            id="demo-user",
            permissions=["*"],  # Full permissions for development
            roles=["admin"],
            metadata={
                "stub": True,
                "environment": "development",
                "username": "demo",  # Store in metadata
            },
        )


# Example: How to replace with bento-security later
"""
from bento_security.providers import LogtoAuthProvider

class LogtoAuthenticator:
    def __init__(self, endpoint: str, app_id: str, app_secret: str | None = None):
        self.provider = LogtoAuthProvider(
            endpoint=endpoint,
            app_id=app_id,
            app_secret=app_secret,
        )

    async def authenticate(self, request: Request) -> CurrentUser | None:
        # Delegate to bento-security
        return await self.provider.authenticate(request)
"""

# Example: How to implement custom JWT authenticator
"""
import jwt
from jwt import PyJWKClient

class JWTAuthenticator:
    def __init__(self, jwks_url: str, audience: str):
        self.jwks_client = PyJWKClient(jwks_url)
        self.audience = audience

    async def authenticate(self, request: Request) -> CurrentUser | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Verify and decode token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
            )

            # Create user from claims
            return CurrentUser(
                id=claims["sub"],
                username=claims.get("username"),
                permissions=claims.get("permissions", []),
                roles=claims.get("roles", []),
                metadata=claims,
            )
        except Exception:
            return None
"""
