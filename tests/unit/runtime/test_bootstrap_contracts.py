from __future__ import annotations

import asyncio

import pytest

from bento.runtime import BentoRuntime, RuntimeBuilder


@pytest.mark.asyncio
async def test_build_async_skips_missing_contracts_when_not_required(tmp_path):
    runtime = (
        RuntimeBuilder()
        .with_config(environment="prod", skip_gates_in_local=False)
        .with_config(contracts_path=str(tmp_path / "missing"), require_contracts=False)
        .build_runtime()
    )
    # Should not raise even though contracts directory is absent
    await runtime.build_async()


def test_build_raises_in_running_loop(monkeypatch):
    runtime = RuntimeBuilder().build_runtime()

    class DummyLoop:
        pass

    # Simulate already-running loop so build() raises RuntimeError
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: DummyLoop())

    with pytest.raises(RuntimeError):
        runtime.build()
