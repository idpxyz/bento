from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

from bento.infrastructure.database.resilience.retry import (
    RetryableOperation,
    RetryConfig,
    retry_on_db_error,
)


class FakeOpError(OperationalError):
    def __init__(self, msg: str):
        super().__init__(msg, None, None)


@pytest.mark.asyncio
async def test_retry_on_db_error_non_retryable_immediate(monkeypatch):
    slept = {"count": 0}

    async def no_sleep(_):
        slept["count"] += 1

    monkeypatch.setattr("asyncio.sleep", no_sleep)

    async def fn():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        await retry_on_db_error(fn)

    assert slept["count"] == 0


@pytest.mark.asyncio
async def test_retry_on_db_error_zero_attempts_raises_runtime():
    async def ok():
        return "x"

    cfg = RetryConfig(max_attempts=0)
    with pytest.raises(RuntimeError):
        await retry_on_db_error(ok, config=cfg)


@pytest.mark.asyncio
async def test_retryable_operation_suppresses_retryable_once(monkeypatch):
    slept = {"count": 0}

    async def no_sleep(_):
        slept["count"] += 1

    monkeypatch.setattr("asyncio.sleep", no_sleep)

    cfg = RetryConfig(max_attempts=2, base_delay=0)
    async with RetryableOperation(cfg):
        raise FakeOpError("connection reset by peer")

    # exception suppressed, sleep called once
    assert slept["count"] == 1


@pytest.mark.asyncio
async def test_retryable_operation_max_attempts_propagates(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("asyncio.sleep", no_sleep)

    cfg = RetryConfig(max_attempts=1)
    with pytest.raises(FakeOpError):
        async with RetryableOperation(cfg):
            raise FakeOpError("connection reset by peer")
