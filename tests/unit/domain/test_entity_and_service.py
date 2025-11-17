from __future__ import annotations

from bento.core.ids import ID
from bento.domain.entity import Entity
from bento.domain.service import DomainService


def test_entity_holds_id():
    e = Entity(id=ID.generate())
    assert e.id is not None and isinstance(str(e.id), str)


class DummyRepo:
    async def get(self, id: ID):
        return None

    async def save(self, entity: Entity):
        return None

    async def list(self) -> list[Entity]:
        return []


def test_domain_service_repository_injection():
    repo = DummyRepo()
    svc = DomainService[Entity](repository=repo)
    assert svc.repository is repo
