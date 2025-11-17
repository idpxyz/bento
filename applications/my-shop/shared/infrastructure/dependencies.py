"""API Dependencies - Uses Bento Framework

This module provides FastAPI dependencies using Bento's infrastructure:
- Database session management
- Unit of Work pattern
- Repository access
"""

from collections.abc import AsyncGenerator

from bento.infrastructure.database import create_async_engine_from_config
from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import settings

# Create database engine using Bento's configuration
db_config = settings.get_database_config()
engine = create_async_engine_from_config(db_config)

# Create session factory
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_uow(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
    """
    Get Unit of Work with Outbox pattern support.

    The UnitOfWork manages:
    - Transaction boundaries
    - Repository lifecycle
    - Event collection and publishing

    Usage:
        @router.post("/products")
        async def create_product(
            data: ProductCreate,
            uow: SQLAlchemyUnitOfWork = Depends(get_uow)
        ):
            async with uow:
                # Register repositories
                from contexts.catalog.infrastructure.repositories.product_repository import ProductRepository
                uow.register_repository(Product, lambda s: ProductRepository(s))

                # Use repository
                repo = uow.repository(Product)
                product = Product.create(...)
                await repo.save(product)
                uow.track(product)

                # Commit (saves changes + publishes events)
                await uow.commit()
    """
    outbox = SqlAlchemyOutbox(session)
    uow = SQLAlchemyUnitOfWork(session, outbox)

    try:
        yield uow
    finally:
        # Cleanup is handled by UnitOfWork's __aexit__
        pass


async def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    """
    Get Unit of Work with all repositories registered.

    This is the recommended way to get UoW for use cases.
    All domain repositories are pre-registered.

    Usage in Use Cases:
        uow = await get_unit_of_work()
        user_repo = uow.repository(User)
        ...
    """
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)

        # Register all repositories
        from contexts.catalog.infrastructure.repositories.category_repository_impl import (
            CategoryRepository,
        )

        from contexts.catalog.domain.category import Category
        from contexts.catalog.domain.product import Product
        from contexts.catalog.infrastructure.repositories.product_repository_impl import (
            ProductRepository,
        )
        from contexts.identity.domain.models.user import User
        from contexts.identity.infrastructure.repositories.user_repository_impl import (
            UserRepository,
        )

        uow.register_repository(User, lambda s: UserRepository(s))
        uow.register_repository(Product, lambda s: ProductRepository(s))
        uow.register_repository(Category, lambda s: CategoryRepository(s))

        return uow


# Convenience function to get specific repositories
# You can add more as needed

# def get_product_repository(
#     session: AsyncSession = Depends(get_db_session)
# ) -> ProductRepository:
#     """Get Product repository."""
#     from contexts.catalog.infrastructure.repositories.product_repository import ProductRepository
#     return ProductRepository(session)


# def get_order_repository(
#     session: AsyncSession = Depends(get_db_session)
# ) -> OrderRepository:
#     """Get Order repository."""
#     from contexts.ordering.infrastructure.repositories.order_repository import OrderRepository
#     return OrderRepository(session)
