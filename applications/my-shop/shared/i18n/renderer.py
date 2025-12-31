"""Message renderer implementation for my-shop.

Implements Bento Framework's IMessageRenderer interface.
"""

from typing import Any


class MessageRenderer:
    """Message renderer for my-shop application.

    Implements the IMessageRenderer protocol from bento.core.i18n.
    """

    def __init__(self, catalog: dict, default_locale: str = "en-US"):
        """Initialize message renderer.

        Args:
            catalog: Translation catalog dictionary
            default_locale: Default locale code (e.g., "en-US", "zh-CN")
        """
        self._catalog = catalog
        self._default = default_locale

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
        # Use provided locale or default
        loc = locale or self._default

        # Get message from catalog
        msg = self._catalog.get(loc, {}).get(reason_code)

        # Fall back if not found
        if not msg:
            msg = fallback

        # Support interpolation if context provided
        if context and msg:
            try:
                msg = msg.format(**context)
            except (KeyError, ValueError):
                # If interpolation fails, return message as-is
                pass

        return msg
