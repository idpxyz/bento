"""Security providers for Bento Framework.

This module provides authenticator implementations for popular
identity providers.

Available Providers:
- LogtoAuthenticator: Logto (https://logto.io)
- Auth0Authenticator: Auth0 (https://auth0.com)
- KeycloakAuthenticator: Keycloak (https://keycloak.org)

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

from bento.security.providers.logto import LogtoAuthenticator
from bento.security.providers.auth0 import Auth0Authenticator
from bento.security.providers.keycloak import KeycloakAuthenticator
from bento.security.providers.base import JWTAuthenticatorBase
from bento.security.providers.m2m import M2MAuthMixin, M2MConfig

__all__ = [
    # Base
    "JWTAuthenticatorBase",
    # M2M
    "M2MAuthMixin",
    "M2MConfig",
    # Providers
    "LogtoAuthenticator",
    "Auth0Authenticator",
    "KeycloakAuthenticator",
]
