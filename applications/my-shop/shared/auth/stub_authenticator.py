"""Stub authenticator for my-shop application.

This is a P0 stub implementation for development/testing.
In production, replace with real authentication (JWT, OAuth, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request

from bento.security import CurrentUser


class StubAuthenticator:
    """Stub authenticator for development/testing.

    This authenticator:
    - Accepts all requests as authenticated
    - Returns a demo user with full permissions
    - Should be replaced in production

    Production replacements:
    - JWTAuthenticator (custom implementation)
    - bento-security providers (LogtoAuthProvider, Auth0AuthProvider, etc.)
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
        # 2. Verify token signature
        # 3. Extract user claims
        # 4. Return CurrentUser with real permissions

        return CurrentUser(
            id="demo-user",
            permissions=("*",),  # Full permissions for development
            roles=("admin",),
            metadata={
                "stub": True,
                "environment": "development",
                "username": "demo",
            },
        )
