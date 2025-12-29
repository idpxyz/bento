from __future__ import annotations

from loms.shared.infra.db.base import Base

def register_all_models() -> None:
    """Import ORM models to ensure they are registered on Base.metadata.

    Notes:
    - Keep this as the single source of truth for ORM model registration.
    - BCs should add their models here (or provide a BC-level register() that is called here).
    """
    # Platform Core models
    from loms.shared.infra.idempotency.models import IdempotencyRecord  # noqa: F401
    from loms.shared.infra.inbox.models import InboxEvent  # noqa: F401
    # Outbox uses Bento's OutboxRecord (now shares same Base)
    from bento.persistence.outbox import OutboxRecord  # noqa: F401

    # Future: BC models
    # from loms.contexts.fulfillment.infra.models import ...  # noqa: F401


def get_metadata():
    register_all_models()
    return Base.metadata
