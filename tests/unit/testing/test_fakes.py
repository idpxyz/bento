"""Tests for fake implementations in bento.testing module."""

from __future__ import annotations

import pytest

from bento.testing.fakes import (
    FakeIdempotencyStore,
    FakeUnitOfWork,
    InMemoryRepository,
)


class TestInMemoryRepository:
    """Test InMemoryRepository."""

    @pytest.mark.asyncio
    async def test_save_and_get(self):
        """Test saving and retrieving entity."""
        repo = InMemoryRepository()
        entity = type("Entity", (), {"id": "123", "name": "test"})()

        await repo.save(entity)
        result = await repo.get("123")

        assert result is not None
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Test getting non-existent entity."""
        repo = InMemoryRepository()
        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id(self):
        """Test find_by_id alias."""
        repo = InMemoryRepository()
        entity = type("Entity", (), {"id": "123", "name": "test"})()

        await repo.save(entity)
        result = await repo.find_by_id("123")

        assert result is not None
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting entity."""
        repo = InMemoryRepository()
        entity = type("Entity", (), {"id": "123", "name": "test"})()

        await repo.save(entity)
        await repo.delete(entity)
        result = await repo.get("123")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_all(self):
        """Test finding all entities."""
        repo = InMemoryRepository()
        entity1 = type("Entity", (), {"id": "1", "name": "test1"})()
        entity2 = type("Entity", (), {"id": "2", "name": "test2"})()

        await repo.save(entity1)
        await repo.save(entity2)
        results = await repo.find_all()

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test checking entity existence."""
        repo = InMemoryRepository()
        entity = type("Entity", (), {"id": "123", "name": "test"})()

        await repo.save(entity)

        assert await repo.exists("123") is True
        assert await repo.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_count(self):
        """Test counting entities."""
        repo = InMemoryRepository()
        entity1 = type("Entity", (), {"id": "1", "name": "test1"})()
        entity2 = type("Entity", (), {"id": "2", "name": "test2"})()

        await repo.save(entity1)
        await repo.save(entity2)

        assert await repo.count() == 2

    def test_clear(self):
        """Test clearing repository."""
        repo = InMemoryRepository()
        entity = type("Entity", (), {"id": "123", "name": "test"})()
        repo._store["123"] = entity

        repo.clear()

        assert len(repo._store) == 0

    def test_set_id_extractor(self):
        """Test setting custom ID extractor."""
        repo = InMemoryRepository()
        repo.set_id_extractor(lambda e: e.custom_id)

        entity = type("Entity", (), {"custom_id": "custom-123"})()
        repo._store["custom-123"] = entity

        assert repo._id_extractor is not None

    @pytest.mark.asyncio
    async def test_id_extractor_usage(self):
        """Test using custom ID extractor."""
        repo = InMemoryRepository()
        repo.set_id_extractor(lambda e: e.custom_id)

        entity = type("Entity", (), {"custom_id": "custom-123"})()
        await repo.save(entity)

        result = await repo.get("custom-123")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_with_value_object_id(self):
        """Test getting entity with value object ID."""
        repo = InMemoryRepository()
        value_obj = type("ValueObject", (), {"value": "123"})()
        entity = type("Entity", (), {"id": value_obj})()

        await repo.save(entity)
        result = await repo.get(value_obj)

        assert result is not None


class TestFakeIdempotencyStore:
    """Test FakeIdempotencyStore."""

    @pytest.mark.asyncio
    async def test_store_and_get_response(self):
        """Test storing and retrieving response."""
        store = FakeIdempotencyStore()
        response = {"id": "123", "status": "created"}

        await store.store_response("key-1", response, request_hash="abc")
        cached = await store.get_response("key-1")

        assert cached is not None
        assert cached.request_hash == "abc"
        assert cached.response_body == response

    @pytest.mark.asyncio
    async def test_get_nonexistent_response(self):
        """Test getting non-existent response."""
        store = FakeIdempotencyStore()
        result = await store.get_response("nonexistent")
        assert result is None

    def test_clear(self):
        """Test clearing store."""
        store = FakeIdempotencyStore()
        store._store["key-1"] = {"request_hash": "abc", "response_body": {}}

        store.clear()

        assert len(store._store) == 0


class TestFakeUnitOfWork:
    """Test FakeUnitOfWork."""

    def test_register_repository(self):
        """Test registering repository."""
        uow = FakeUnitOfWork()

        class Order:
            pass

        uow.register_repository(Order, InMemoryRepository)
        repo = uow.repository(Order)

        assert repo is not None
        assert isinstance(repo, InMemoryRepository)

    def test_repository_auto_create(self):
        """Test auto-creating repository."""
        uow = FakeUnitOfWork()

        class Order:
            pass

        repo = uow.repository(Order)

        assert repo is not None
        assert isinstance(repo, InMemoryRepository)

    def test_track_aggregate(self):
        """Test tracking aggregate."""
        uow = FakeUnitOfWork()
        aggregate = type("Aggregate", (), {})()

        uow.track(aggregate)

        assert len(uow.tracked_aggregates) == 1
        assert uow.tracked_aggregates[0] is aggregate

    def test_set_tenant_id(self):
        """Test setting tenant ID."""
        uow = FakeUnitOfWork()
        uow.set_tenant_id("tenant-123")

        assert uow._tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_commit(self):
        """Test commit."""
        uow = FakeUnitOfWork()

        await uow.commit()

        assert uow.was_committed is True

    @pytest.mark.asyncio
    async def test_rollback(self):
        """Test rollback."""
        uow = FakeUnitOfWork()

        await uow.rollback()

        assert uow.was_committed is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using as context manager."""
        uow = FakeUnitOfWork()

        async with uow:
            pass

        assert uow.was_committed is True

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self):
        """Test context manager with exception."""
        uow = FakeUnitOfWork()

        try:
            async with uow:
                raise ValueError("test error")
        except ValueError:
            pass

        assert uow.was_committed is False

    def test_reset(self):
        """Test resetting UoW state."""
        uow = FakeUnitOfWork()
        aggregate = type("Aggregate", (), {})()

        uow.track(aggregate)
        uow._committed = True
        uow.set_tenant_id("tenant-123")

        uow.reset()

        assert len(uow.tracked_aggregates) == 0
        assert uow.was_committed is False
        assert uow._tenant_id is None
