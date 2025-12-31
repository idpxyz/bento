"""i18n support for my-shop application.

This module provides internationalization support using Bento Framework's
optional i18n mechanism.
"""

from shared.i18n.catalog import CATALOG
from shared.i18n.renderer import MessageRenderer

__all__ = ["CATALOG", "MessageRenderer"]
