from __future__ import annotations

from bento.core.ids import ID
from bento.domain.entity import Entity
from bento.domain.ports.repository import Repository
from bento.domain.service import DomainService


def test_entity_holds_id():
    e = Entity(id=ID.generate())
    assert e.id is not None and isinstance(str(e.id), str)


class DummyRepo(Repository[Entity, ID]):
    """测试用的简单 Repository 实现"""

    async def get(self, id: ID) -> Entity | None:
        return None

    async def save(self, entity: Entity) -> Entity:
        return entity

    async def delete(self, entity: Entity) -> None:
        pass

    async def find_all(self) -> list[Entity]:
        return []

    async def exists(self, id: ID) -> bool:
        return False

    async def count(self) -> int:
        return 0


def test_domain_service_repository_injection():
    repo = DummyRepo()
    svc = DomainService[Entity, ID](repository=repo)
    assert svc._repository is repo
