import importlib

import pytest
from sqlalchemy import event


@pytest.mark.asyncio
async def test_enable_outbox_listener_idempotent(monkeypatch):
    calls: list[tuple] = []

    def fake_listen(target, identifier, fn, propagate=False, **kwargs):  # noqa: ANN001
        if identifier == "before_commit":
            calls.append((target, identifier, fn, propagate))

    # Patch sqlalchemy.event.listen BEFORE any import of the target module
    monkeypatch.setattr(event, "listen", fake_listen, raising=True)

    # Remove any already-loaded module to ensure clean import under patch
    import sys

    mod_name = "bento.persistence.outbox.listener"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    # First import should install once (under patch)
    mod = importlib.import_module(mod_name)
    assert len(calls) == 1

    # Repeated enable should be no-op
    mod.enable_outbox_listener()
    mod.enable_outbox_listener()
    assert len(calls) == 1

    # Reload should reset module state and install once more
    importlib.reload(mod)
    assert len(calls) == 2
