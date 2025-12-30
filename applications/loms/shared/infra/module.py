"""
Infrastructure Module - provides shared infrastructure capabilities.

Registers:
- Database session factory
- Idempotency service
- Outbox uses Bento's implementation (bento.persistence.outbox)
"""

from bento.runtime import BentoModule


class InfraModule(BentoModule):
    """Infrastructure module using BentoModule."""

    name = "infra"
    requires = ()

    async def on_register(self, container) -> None:
        """Register infrastructure components into the container."""
        # Database session
        from loms.shared.infra.db.session import AsyncSessionMaker

        container.set("db.session_maker", AsyncSessionMaker)

        # Idempotency service
        from loms.shared.infra.idempotency.service import IdempotencyService

        container.set("idempotency.service_class", IdempotencyService)

        # Outbox: Use Bento's SqlAlchemyOutbox
        from bento.persistence.outbox import SqlAlchemyOutbox

        container.set("outbox.class", SqlAlchemyOutbox)
