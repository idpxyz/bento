from loms.shared.platform.runtime.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(settings.database.url, echo=False, pool_pre_ping=True, future=True)
AsyncSessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with AsyncSessionMaker() as session:
        yield session
