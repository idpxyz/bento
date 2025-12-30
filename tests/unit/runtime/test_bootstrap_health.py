from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bento.runtime import RuntimeBuilder


@pytest.mark.asyncio
async def test_health_no_db_no_contracts(tmp_path):
    runtime = (
        RuntimeBuilder()
        .with_config(environment="prod", skip_gates_in_local=False)
        .with_config(contracts_path=str(tmp_path / "missing"), require_contracts=False)
        .build_runtime()
    )

    app = runtime.create_fastapi_app(title="HealthOnly")

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "healthy"
        assert payload.get("database") is None or payload.get("database") in ("unknown",)
