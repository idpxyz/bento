"""FastAPI middleware for security.

This module provides middleware for automatic authentication setup
in FastAPI applications.

Example:
    ```python
    from fastapi import FastAPI
    from bento.security import add_security_middleware

    app = FastAPI()
    add_security_middleware(
        app,
        authenticator=MyJWTAuthenticator(),
        require_auth=False,
    )
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from bento.security.context import SecurityContext
from bento.security.ports import IAuthenticator


def add_security_middleware(
    app: "FastAPI",
    authenticator: IAuthenticator,
    require_auth: bool = False,
    exclude_paths: list[str] | None = None,
) -> None:
    """Add security middleware to FastAPI application.

    This middleware:
    1. Calls the authenticator for each request
    2. Sets SecurityContext with the authenticated user
    3. Optionally requires authentication for all requests

    Args:
        app: FastAPI application instance
        authenticator: IAuthenticator implementation
        require_auth: If True, return 401 when not authenticated
        exclude_paths: Paths to exclude from authentication
                      (e.g., ["/health", "/docs"])

    Example:
        ```python
        from fastapi import FastAPI
        from bento.security import add_security_middleware

        app = FastAPI()

        add_security_middleware(
            app,
            authenticator=JWTAuthenticator(jwks_url="..."),
            require_auth=True,
            exclude_paths=["/health", "/docs", "/openapi.json"],
        )
        ```
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    exclude_paths = exclude_paths or []

    @app.middleware("http")
    async def security_middleware(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        call_next,
    ):
        # Check if path is excluded
        path = request.url.path
        if any(path.startswith(ep) for ep in exclude_paths):
            return await call_next(request)

        # Authenticate
        user = await authenticator.authenticate(request)

        # Check if auth is required
        if require_auth and not user:
            return JSONResponse(
                status_code=401,
                content={
                    "reason_code": "UNAUTHORIZED",
                    "message": "Authentication required",
                    "category": "client",
                    "details": {},
                    "retryable": False,
                },
            )

        # Set security context
        SecurityContext.set_user(user)

        # Also set on request.state for compatibility
        request.state.user = user

        try:
            response = await call_next(request)
            return response
        finally:
            # Always clear context
            SecurityContext.clear()
