from sqlalchemy.ext.asyncio import AsyncSession
from loms.contexts.shipment.infra.persistence.repositories.shipment_repo import ShipmentRepositoryImpl
from loms.contexts.shipment.infra.persistence.repositories.idempotency_repo import IdempotencyRepositoryImpl
from bento.persistence.outbox import SqlAlchemyOutbox

class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._shipments = ShipmentRepositoryImpl(session)
        self._idempotency = IdempotencyRepositoryImpl(session)
        self._outbox = SqlAlchemyOutbox(session)
        self._tx = None

    async def __aenter__(self):
        # Don't start a new transaction if one is already active
        if not self.session.in_transaction():
            self._tx = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self.rollback()
        else:
            # default: if caller did not commit explicitly, rollback to avoid implicit commits
            # caller should call commit()
            await self.rollback()

    async def commit(self) -> None:
        if self._tx:
            await self._tx.commit()
            self._tx = None

    async def rollback(self) -> None:
        if self._tx:
            await self._tx.rollback()
            self._tx = None

    @property
    def shipments(self):
        return self._shipments

    @property
    def idempotency(self):
        return self._idempotency

    @property
    def outbox(self):
        return self._outbox
