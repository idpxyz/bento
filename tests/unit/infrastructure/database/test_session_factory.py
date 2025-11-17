from __future__ import annotations

import pytest

from bento.infrastructure.database.config import DatabaseConfig
from bento.infrastructure.database.session import (
    create_async_engine_from_config,
    create_async_session_factory,
)


@pytest.mark.asyncio
async def test_create_engine_legacy_branch_and_session_factory():
    cfg = DatabaseConfig(url="sqlite+aiosqlite:///:memory:", echo=False)

    # legacy path (use_engine_abstraction=False) to cover lines 68-72
    engine = create_async_engine_from_config(cfg, use_engine_abstraction=False)
    try:
        factory = create_async_session_factory(engine)
        async with factory() as session:  # smoke
            assert session.bind is engine
    finally:
        await engine.dispose()
