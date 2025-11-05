from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW
from idp.framework.infrastructure.persistence.core import AbstractRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus


class SqlAlchemyAsyncUoWRepo(SqlAlchemyAsyncUoW):
    def __init__(self, sf: async_sessionmaker[AsyncSession], bus: AbstractEventBus, repo_map: dict[str, AbstractRepository]):
        super().__init__(sf, bus)
        self.repo_map = repo_map or {}  # e.g. {"order": OrderRepository, ...}

    async def __aenter__(self):
        await super().__aenter__()
        # 批量实例化并挂到 uow.repos
        self.repos = {
            name: repo_cls(self.session)
            for name, repo_cls in self.repo_map.items()
        }
        return self

    # 这样，在业务层就能通过 uow.repos["order"]、uow.repos["customer"] 直接拿到对应仓储
