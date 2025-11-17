from __future__ import annotations

import asyncio

import pytest

from bento.infrastructure.database.resilience.errors import OperationalError
from bento.infrastructure.database.resilience.retry import RetryConfig, retry_on_db_error


@pytest.mark.asyncio
async def test_retry_on_db_error_succeeds_after_retries(monkeypatch):
    calls = {"n": 0}

    class FakeOpError(OperationalError):
        def __init__(self):
            super().__init__("op", None, None)

    async def sleeper(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", sleeper)

    async def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeOpError()
        return 42

    cfg = RetryConfig(max_attempts=5, base_delay=0.0, jitter=False)
    out = await retry_on_db_error(fn, cfg)
    assert out == 42
    assert calls["n"] == 3
