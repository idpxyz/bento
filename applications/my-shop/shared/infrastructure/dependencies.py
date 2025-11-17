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
    Get Unit of Work with Outbox pattern support and all repositories registered.

    The UnitOfWork manages:
    - Transaction boundaries
    - Repository lifecycle
    - Event collection and publishing
    - All domain repositories are pre-registered

    Usage:
        @router.post("/products")
        async def create_product(
            data: ProductCreate,
            uow: SQLAlchemyUnitOfWork = Depends(get_uow)
        ):
            async with uow:
                # Use repository (already registered)
                repo = uow.repository(Product)
                product = Product.create(...)
                await repo.save(product)
                # No need to manually track - repository handles it

                # Commit (saves changes + publishes events)
                await uow.commit()
    """
    outbox = SqlAlchemyOutbox(session)
    uow = SQLAlchemyUnitOfWork(session, outbox)

    # Register all domain repositories upfront
    from contexts.catalog.domain.category import Category
    from contexts.catalog.domain.product import Product
    from contexts.catalog.infrastructure.repositories.category_repository_impl import (
        CategoryRepository,
    )
    from contexts.catalog.infrastructure.repositories.product_repository_impl import (
        ProductRepository,
    )
    from contexts.identity.domain.models.user import User
    from contexts.identity.infrastructure.repositories.user_repository_impl import (
        UserRepository,
    )
    from contexts.ordering.domain.order import Order
    from contexts.ordering.infrastructure.repositories.order_repository_impl import (
        OrderRepository,
    )

    uow.register_repository(User, lambda s: UserRepository(s))
    uow.register_repository(Product, lambda s: ProductRepository(s))
    uow.register_repository(Category, lambda s: CategoryRepository(s))
    uow.register_repository(Order, lambda s: OrderRepository(s))

    try:
        yield uow
    finally:
        # Cleanup is handled by UnitOfWork's __aexit__
        pass


# ==================== DEPRECATED ====================
# The following function has been removed due to Session lifecycle issues.
# Use get_uow() with Depends() instead.
#
# Old pattern (INCORRECT - Session closes before use):
#     async def get_create_order_use_case() -> CreateOrderUseCase:
#         uow = await get_unit_of_work()  # ❌ Session already closed
#         return CreateOrderUseCase(uow)
#
# New pattern (CORRECT):
#     async def get_create_order_use_case(
#         uow: SQLAlchemyUnitOfWork = Depends(get_uow)
#     ) -> CreateOrderUseCase:
#         return CreateOrderUseCase(uow)  # ✅ Session managed by FastAPI
# ===================================================
