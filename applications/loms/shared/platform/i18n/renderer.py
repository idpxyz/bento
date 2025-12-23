from loms.shared.platform.i18n.catalog import CATALOG
from loms.shared.platform.runtime.settings import settings

class MessageRenderer:
    def __init__(self, default_locale: str | None = None):
        self._default = default_locale or settings.app.default_locale

    def render(self, reason_code: str, fallback: str, locale: str | None = None) -> str:
        loc = locale or self._default
        msg = CATALOG.get(loc, {}).get(reason_code)
        return msg or fallback or reason_code
