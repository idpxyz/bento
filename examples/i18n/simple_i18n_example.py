"""Simple i18n example for Bento Framework.

This example demonstrates how to implement optional i18n support
using Bento's IMessageRenderer interface.
"""

from bento.core import (
    DomainException,
    IMessageRenderer,
    LocaleContext,
    set_global_message_renderer,
)


# Step 1: Define translation catalog
CATALOG = {
    "zh-CN": {
        "STATE_CONFLICT": "当前状态不允许此操作",
        "NOT_FOUND": "资源不存在",
        "VALIDATION_FAILED": "参数校验失败: {field}",
        "UNAUTHORIZED": "需要身份认证",
        "FORBIDDEN": "访问被拒绝",
    },
    "en-US": {
        "STATE_CONFLICT": "Current state does not allow this operation",
        "NOT_FOUND": "Resource not found",
        "VALIDATION_FAILED": "Validation failed: {field}",
        "UNAUTHORIZED": "Authentication required",
        "FORBIDDEN": "Access denied",
    },
}


# Step 2: Implement IMessageRenderer
class SimpleMessageRenderer:
    """Simple message renderer implementation."""

    def __init__(self, catalog: dict, default_locale: str = "en-US"):
        self._catalog = catalog
        self._default = default_locale

    def render(
        self,
        reason_code: str,
        fallback: str,
        locale: str | None = None,
        **context,
    ) -> str:
        """Render message with i18n support."""
        loc = locale or self._default
        msg = self._catalog.get(loc, {}).get(reason_code, fallback)

        # Support interpolation
        if context:
            try:
                msg = msg.format(**context)
            except (KeyError, ValueError):
                # Fall back if interpolation fails
                pass

        return msg


# Step 3: Demo usage
def demo_without_i18n():
    """Demo: Exceptions without i18n (default behavior)."""
    print("=" * 60)
    print("Demo 1: Without i18n (default behavior)")
    print("=" * 60)

    try:
        raise DomainException(
            reason_code="STATE_CONFLICT",
            message="Default English message"
        )
    except DomainException as e:
        print(f"Exception: {e.message}")
        print(f"Reason Code: {e.reason_code}")
    print()


def demo_with_i18n_english():
    """Demo: Exceptions with i18n (English)."""
    print("=" * 60)
    print("Demo 2: With i18n (English)")
    print("=" * 60)

    # Register renderer
    renderer = SimpleMessageRenderer(CATALOG, default_locale="en-US")
    set_global_message_renderer(renderer)

    # Set locale
    LocaleContext.set("en-US")

    try:
        raise DomainException(reason_code="STATE_CONFLICT")
    except DomainException as e:
        print(f"Exception: {e.message}")
        print(f"Locale: {LocaleContext.get()}")

    # Cleanup
    LocaleContext.clear()
    set_global_message_renderer(None)
    print()


def demo_with_i18n_chinese():
    """Demo: Exceptions with i18n (Chinese)."""
    print("=" * 60)
    print("Demo 3: With i18n (Chinese)")
    print("=" * 60)

    # Register renderer
    renderer = SimpleMessageRenderer(CATALOG, default_locale="zh-CN")
    set_global_message_renderer(renderer)

    # Set locale
    LocaleContext.set("zh-CN")

    try:
        raise DomainException(reason_code="STATE_CONFLICT")
    except DomainException as e:
        print(f"Exception: {e.message}")
        print(f"Locale: {LocaleContext.get()}")

    try:
        raise DomainException(reason_code="NOT_FOUND")
    except DomainException as e:
        print(f"Exception: {e.message}")

    # Cleanup
    LocaleContext.clear()
    set_global_message_renderer(None)
    print()


def demo_with_interpolation():
    """Demo: Message interpolation."""
    print("=" * 60)
    print("Demo 4: Message interpolation")
    print("=" * 60)

    # Register renderer
    renderer = SimpleMessageRenderer(CATALOG, default_locale="zh-CN")
    set_global_message_renderer(renderer)

    # Set locale
    LocaleContext.set("zh-CN")

    try:
        raise DomainException(
            reason_code="VALIDATION_FAILED",
            details={"field": "email"}  # Pass via details for interpolation
        )
    except DomainException as e:
        print(f"Exception: {e.message}")
        print(f"Details: {e.details}")

    # Cleanup
    LocaleContext.clear()
    set_global_message_renderer(None)
    print()


def demo_fallback_behavior():
    """Demo: Fallback when translation not found."""
    print("=" * 60)
    print("Demo 5: Fallback behavior")
    print("=" * 60)

    # Register renderer
    renderer = SimpleMessageRenderer(CATALOG, default_locale="zh-CN")
    set_global_message_renderer(renderer)

    # Set locale
    LocaleContext.set("zh-CN")

    try:
        # This reason code doesn't exist in catalog
        raise DomainException(
            reason_code="CUSTOM_ERROR",
            message="Custom fallback message"
        )
    except DomainException as e:
        print(f"Exception: {e.message}")
        print("(Using fallback because translation not found)")

    # Cleanup
    LocaleContext.clear()
    set_global_message_renderer(None)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Bento Framework - i18n Examples")
    print("=" * 60 + "\n")

    demo_without_i18n()
    demo_with_i18n_english()
    demo_with_i18n_chinese()
    demo_with_interpolation()
    demo_fallback_behavior()

    print("=" * 60)
    print("All demos completed!")
    print("=" * 60)
