"""Security integration for Bento Runtime.

This module provides convenient setup functions for integrating
security features into FastAPI applications.

Example:
    ```python
    from bento.runtime.integrations import setup_security
    from bento.security import IAuthenticator

    app = FastAPI()
    setup_security(app, authenticator=MyAuthenticator())
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from bento.security import add_security_middleware
from bento.security.ports import IAuthenticator


def setup_security(
    app: FastAPI,
    authenticator: IAuthenticator,
    require_auth: bool = False,
    exclude_paths: list[str] | None = None,
) -> None:
    """Setup security for Bento application.

    This is a convenience wrapper around bento.security's
    add_security_middleware function, providing a unified
    integration point in bento.runtime.

    Args:
        app: FastAPI application
        authenticator: IAuthenticator implementation
        require_auth: If True, require authentication for all requests
        exclude_paths: Paths to exclude from authentication

    Example:
        ```python
        from bento.runtime.integrations import setup_security
        from my_app.auth import JWTAuthenticator

        app = FastAPI()
        setup_security(
            app,
            authenticator=JWTAuthenticator(jwks_url="..."),
            require_auth=True,
            exclude_paths=["/health", "/docs"],
        )
        ```
    """
    add_security_middleware(
        app,
        authenticator=authenticator,
        require_auth=require_auth,
        exclude_paths=exclude_paths,
    )
