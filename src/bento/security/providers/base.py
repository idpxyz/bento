"""Base class for JWT-based authenticators.

This module provides a base class with common JWT verification logic
that can be extended by specific provider implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field

from bento.security.models import CurrentUser
from bento.security.ports import IAuthenticator


@dataclass
class JWTConfig:
    """Configuration for JWT verification.

    Attributes:
        jwks_url: URL to fetch JSON Web Key Set
        issuer: Expected token issuer
        audience: Expected token audience
        algorithms: Allowed signing algorithms
        jwks_cache_ttl: JWKS cache TTL in seconds (default: 300)
    """

    jwks_url: str
    issuer: str
    audience: str | None = None
    algorithms: list[str] = field(default_factory=lambda: ["RS256"])
    jwks_cache_ttl: int = 300  # 5 minutes


class JWTAuthenticatorBase(IAuthenticator, ABC):
    """Base class for JWT-based authenticators.

    Provides common JWT verification logic using JWKS.
    Subclasses must implement `_extract_user_from_claims`.

    Example:
        ```python
        class MyAuthenticator(JWTAuthenticatorBase):
            def __init__(self, endpoint: str):
                config = JWTConfig(
                    jwks_url=f"{endpoint}/.well-known/jwks.json",
                    issuer=endpoint,
                )
                super().__init__(config)

            def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
                return CurrentUser(
                    id=claims["sub"],
                    permissions=claims.get("permissions", []),
                )
        ```
    """

    _jwks_client_cache: dict = {}  # Class-level cache for PyJWKClient instances

    def __init__(self, config: JWTConfig):
        """Initialize with JWT configuration.

        Args:
            config: JWT verification configuration
        """
        self.config = config
        self._jwks_client: Any | None = None

    async def authenticate(self, request: Any) -> CurrentUser | None:
        """Authenticate request using JWT token.

        Args:
            request: FastAPI Request object

        Returns:
            CurrentUser if authenticated, None otherwise
        """
        token = self._extract_token(request)
        if not token:
            return None

        try:
            claims = await self._verify_token(token)
            return self._extract_user_from_claims(claims)
        except Exception:
            return None

    def _extract_token(self, request: Any) -> str | None:
        """Extract JWT token from Authorization header.

        Args:
            request: FastAPI Request object

        Returns:
            Token string or None
        """
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _get_jwks_client(self):
        """Get or create cached PyJWKClient.

        Returns a cached client for the JWKS URL to avoid
        repeated network requests for the same keys.

        Returns:
            PyJWKClient instance
        """
        try:
            from jwt import PyJWKClient
        except ImportError as err:
            raise ImportError(
                "PyJWT is required for JWT verification. "
                "Install it with: pip install PyJWT[crypto]"
            ) from err

        jwks_url = self.config.jwks_url

        # Check class-level cache
        if jwks_url not in JWTAuthenticatorBase._jwks_client_cache:
            # Create client with caching enabled
            JWTAuthenticatorBase._jwks_client_cache[jwks_url] = PyJWKClient(
                jwks_url,
                cache_jwk_set=True,
                lifespan=self.config.jwks_cache_ttl,
            )

        return JWTAuthenticatorBase._jwks_client_cache[jwks_url]

    async def _verify_token(self, token: str) -> dict:
        """Verify JWT token and return claims.

        Args:
            token: JWT token string

        Returns:
            Token claims

        Raises:
            Exception: If token is invalid
        """
        try:
            import jwt
        except ImportError as err:
            raise ImportError(
                "PyJWT is required for JWT verification. "
                "Install it with: pip install PyJWT[crypto]"
            ) from err

        # Get signing key from cached JWKS client
        jwks_client = self._get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Verify token
        options = {"verify_aud": self.config.audience is not None}
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=self.config.algorithms,
            issuer=self.config.issuer,
            audience=self.config.audience,
            options=options,
        )

        return claims

    @abstractmethod
    def _extract_user_from_claims(self, claims: dict) -> CurrentUser:
        """Extract CurrentUser from verified token claims.

        Args:
            claims: Verified JWT claims

        Returns:
            CurrentUser instance
        """
        ...
