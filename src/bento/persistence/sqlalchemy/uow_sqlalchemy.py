from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .base import session_scope


class SqlAlchemyUnitOfWork:
    session: AsyncSession | None = None

    async def __aenter__(self):
        cm = session_scope()
        self._cm = cm  # type: ignore[attr-defined]
        self.session = await cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self._cm.__aexit__(exc_type, exc, tb)  # type: ignore[attr-defined]
        finally:
            self.session = None

    async def commit(self):
        if self.session:
            await self.session.commit()

    async def rollback(self):
        if self.session:
            await self.session.rollback()
