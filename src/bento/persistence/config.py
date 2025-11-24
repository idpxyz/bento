from __future__ import annotations

import os


def is_outbox_listener_enabled() -> bool:
    v = os.getenv("BENTO_OUTBOX_LISTENER", "")
    return v.lower() in ("1", "true", "on", "yes")
