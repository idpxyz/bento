"""API Dependencies - Dependency Injection"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import settings

# Database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.

    Usage in FastAPI:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# TODO: Add more dependencies as needed
# Example:
# def get_current_user(token: str = Depends(oauth2_scheme)):
#     ...
#
# def get_repository(db: AsyncSession = Depends(get_db)):
#     return UserRepository(session=db, actor="system")
