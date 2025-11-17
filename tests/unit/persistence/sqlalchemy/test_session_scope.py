from __future__ import annotations

import pytest

from bento.persistence.sqlalchemy.base import init_async_db, session_scope


@pytest.mark.asyncio
async def test_session_scope_commit_and_close():
    init_async_db("sqlite+aiosqlite:///:memory:")
    async with session_scope() as sess:
        assert sess is not None


@pytest.mark.asyncio
async def test_session_scope_rollback_on_exception():
    init_async_db("sqlite+aiosqlite:///:memory:")
    with pytest.raises(RuntimeError):
        async with session_scope():
            raise RuntimeError("boom")
