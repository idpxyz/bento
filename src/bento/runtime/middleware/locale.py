"""Locale middleware for FastAPI applications.

This middleware provides automatic locale detection and context management
for i18n (internationalization) support.

Usage:
    ```python
    from bento.runtime.middleware import LocaleMiddleware

    app = FastAPI()
    app.add_middleware(
        LocaleMiddleware,
        default_locale="en-US",
        supported_locales=["en-US", "zh-CN"],
    )
    ```
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from bento.core import LocaleContext


class LocaleMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic locale detection and context management.

    Detects user's preferred locale from request headers and sets LocaleContext
    for use by i18n message renderers.

    Features:
    - Automatic locale detection from Accept-Language header
    - Fallback to default locale
    - Supported locales validation
    - Async-safe context management (automatic cleanup)

    Detection Strategy:
    1. Check Accept-Language header
    2. Parse and match against supported locales
    3. Fall back to default locale if no match

    Args:
        app: FastAPI application
        default_locale: Default locale code (default: "en-US")
        supported_locales: List of supported locale codes (default: ["en-US", "zh-CN"])
        header_name: Name of the locale header (default: "Accept-Language")

    Example:
        ```python
        app.add_middleware(
            LocaleMiddleware,
            default_locale="zh-CN",
            supported_locales=["en-US", "zh-CN", "ja-JP"],
        )
        ```
    """

    def __init__(
        self,
        app,
        default_locale: str = "en-US",
        supported_locales: list[str] | None = None,
        header_name: str = "Accept-Language",
    ):
        """Initialize locale middleware.

        Args:
            app: FastAPI application
            default_locale: Default locale code
            supported_locales: List of supported locale codes
            header_name: Name of the locale header
        """
        super().__init__(app)
        self.default_locale = default_locale
        self.supported_locales = supported_locales or ["en-US", "zh-CN"]
        self.header_name = header_name

    def _detect_locale(self, accept_language: str | None) -> str:
        """Detect locale from Accept-Language header.

        Implements simple locale matching:
        - Checks if any supported locale code appears in Accept-Language
        - Returns first match or default locale

        For production, consider using a proper Accept-Language parser
        like `accept-language-parser` or `langcodes`.

        Args:
            accept_language: Accept-Language header value

        Returns:
            Detected locale code
        """
        if not accept_language:
            return self.default_locale

        # Simple matching: check if any supported locale appears in header
        accept_lower = accept_language.lower()

        for locale in self.supported_locales:
            # Match both full locale (zh-CN) and language code (zh)
            locale_lower = locale.lower()
            lang_code = locale_lower.split("-")[0]

            if locale_lower in accept_lower or lang_code in accept_lower:
                return locale

        return self.default_locale

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with locale detection.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response from next middleware
        """
        # Detect locale from header
        accept_language = request.headers.get(self.header_name)
        locale = self._detect_locale(accept_language)

        # Set locale context
        LocaleContext.set(locale)

        try:
            # Process request
            response = await call_next(request)
            return response
        finally:
            # Always clear context after request
            LocaleContext.clear()
