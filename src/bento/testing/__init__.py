"""Bento Testing Utilities.

Provides test doubles and utilities for testing Bento applications.

Example:
    ```python
    from bento.testing import FakeUnitOfWork, InMemoryRepository

    @pytest.fixture
    def uow():
        uow = FakeUnitOfWork()
        return uow

    async def test_create_order(uow):
        handler = CreateOrderHandler(uow)
        result = await handler.execute(command)
        assert result.id is not None
    ```
"""

from bento.testing.fakes import (
    FakeIdempotencyStore,
    FakeUnitOfWork,
    InMemoryRepository,
)

__all__ = [
    "FakeUnitOfWork",
    "FakeIdempotencyStore",
    "InMemoryRepository",
]
