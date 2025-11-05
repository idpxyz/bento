from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[misc]
        return cls.__name__.lower()


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_async_db(dsn: str):
    global _engine, _session_factory
    _engine = create_async_engine(dsn, echo=False, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    assert _session_factory is not None, "Call init_async_db() first"
    session = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
