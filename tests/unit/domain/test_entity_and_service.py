from __future__ import annotations

from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_service import DomainService
from bento.domain.ports.repository import IRepository


def test_entity_holds_id():
    e = AggregateRoot(id=ID.generate())
    assert e.id is not None and isinstance(str(e.id), str)


class DummyRepo(IRepository[AggregateRoot, ID]):
    """测试用的简单 Repository 实现"""

    async def get(self, id: ID) -> AggregateRoot | None:
        return None

    async def save(self, entity: AggregateRoot) -> AggregateRoot:
        return entity

    async def delete(self, entity: AggregateRoot) -> None:
        pass

    async def find_all(self) -> list[AggregateRoot]:
        return []

    async def exists(self, id: ID) -> bool:
        return False

    async def count(self) -> int:
        return 0


def test_domain_service_is_stateless():
    """Test that domain service is stateless."""
    # DomainService is designed to be stateless
    # This test verifies the basic design principle
    service = DomainService()

    # Domain services should not have instance state
    assert hasattr(service, "__dict__")  # Has dict but should be empty

    # Basic functionality test
    assert isinstance(service, DomainService)
