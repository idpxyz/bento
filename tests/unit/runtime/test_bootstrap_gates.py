from __future__ import annotations

import pytest

from bento.runtime import RuntimeBuilder


@pytest.mark.asyncio
async def test_build_async_missing_contracts_raises_when_required(tmp_path):
    runtime = (
        RuntimeBuilder()
        .with_config(environment="prod", skip_gates_in_local=False)
        .with_config(contracts_path=str(tmp_path / "absent"), require_contracts=True)
        .build_runtime()
    )

    with pytest.raises(RuntimeError):
        await runtime.build_async()
