from __future__ import annotations

import importlib.util
import sys

import pytest


@pytest.mark.asyncio
async def test_inmemory_repository_in_file_module_roundtrip():
    path = "src/bento/persistence/repository.py"
    spec = importlib.util.spec_from_file_location("bento.persistence.repository_file", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    # define Entity subclass compatible with module's InMemoryRepository
    from bento.core.ids import EntityId
    from bento.domain.entity import Entity

    class User(Entity):
        name: str  # type: ignore[assignment]

    repo = mod.InMemoryRepository[User]()

    u = User(id=EntityId.generate())
    u.name = "A"  # type: ignore[attr-defined]

    await repo.save(u)
    got = await repo.get(u.id)
    assert got is not None and got.name == "A"  # type: ignore[attr-defined]

    items = await repo.list()
    assert len(items) == 1
