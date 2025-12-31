"""i18n mechanism for Bento framework (Optional).

This module provides OPTIONAL i18n (internationalization) mechanisms.
Applications can choose to implement these interfaces or ignore them entirely.

Design Philosophy:
    - Framework provides MECHANISMS (interfaces, context)
    - Applications provide STRATEGIES (implementations, translations)
    - Zero dependencies (no external i18n libraries)
    - Completely optional (applications can ignore)

Example:
    ```python
    # Application implements the interface
    from bento.core.i18n import IMessageRenderer

    class MessageRenderer:
        def __init__(self, catalog: dict):
            self._catalog = catalog

        def render(self, reason_code: str, fallback: str, locale: str | None = None) -> str:
            locale = locale or "en-US"
            return self._catalog.get(locale, {}).get(reason_code, fallback)

    # Register globally (optional)
    from bento.core.i18n import set_global_message_renderer
    renderer = MessageRenderer(CATALOG)
    set_global_message_renderer(renderer)
    ```
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Protocol

# Global message renderer reference (optional)
_global_message_renderer: Any | None = None


class IMessageRenderer(Protocol):
    """Message renderer interface (Optional).

    Applications can implement this interface to provide i18n support.
    Framework will use it if registered, otherwise falls back to default messages.

    Example:
        ```python
        class MessageRenderer:
            def render(self, reason_code: str, fallback: str, locale: str | None = None) -> str:
                # Your implementation
                return translated_message
        ```
    """

    def render(
        self,
        reason_code: str,
        fallback: str,
        locale: str | None = None,
        **context: Any,
    ) -> str:
        """Render a message for the given reason code.

        Args:
            reason_code: The reason code to translate
            fallback: Default message if translation not found
            locale: Optional locale code (e.g., "en-US", "zh-CN")
            **context: Optional context variables for message interpolation

        Returns:
            Translated message or fallback
        """
        ...


class ILocaleResolver(Protocol):
    """Locale resolver interface (Optional).

    Applications can implement this interface to resolve locale from requests.

    Example:
        ```python
        class HeaderLocaleResolver:
            def resolve(self, request) -> str:
                return request.headers.get("Accept-Language", "en-US")
        ```
    """

    def resolve(self, request: Any) -> str:
        """Resolve locale from request.

        Args:
            request: Request object (framework-agnostic)

        Returns:
            Locale code (e.g., "en-US", "zh-CN")
        """
        ...


# Locale context (async-safe, similar to SecurityContext)
_current_locale: ContextVar[str | None] = ContextVar("current_locale", default=None)


class LocaleContext:
    """Async-safe locale context storage.

    Similar to SecurityContext, provides request-scoped locale storage.

    Example:
        ```python
        # In middleware
        LocaleContext.set("zh-CN")

        # In business code
        locale = LocaleContext.get()  # "zh-CN"

        # Cleanup
        LocaleContext.clear()
        ```
    """

    @classmethod
    def set(cls, locale: str) -> None:
        """Set current locale.

        Args:
            locale: Locale code (e.g., "en-US", "zh-CN")
        """
        _current_locale.set(locale)

    @classmethod
    def get(cls) -> str | None:
        """Get current locale.

        Returns:
            Current locale code or None if not set
        """
        return _current_locale.get()

    @classmethod
    def clear(cls) -> None:
        """Clear current locale."""
        _current_locale.set(None)


def set_global_message_renderer(renderer: IMessageRenderer | None) -> None:
    """Set the global message renderer (Optional).

    Called during application startup to enable i18n support.
    If not set, framework will use default messages.

    Args:
        renderer: IMessageRenderer instance or None to clear

    Example:
        ```python
        # In application startup
        from bento.core.i18n import set_global_message_renderer

        renderer = MessageRenderer(catalog)
        set_global_message_renderer(renderer)
        ```
    """
    global _global_message_renderer
    _global_message_renderer = renderer


def get_global_message_renderer() -> IMessageRenderer | None:
    """Get the global message renderer.

    Returns:
        Registered IMessageRenderer instance or None
    """
    return _global_message_renderer
