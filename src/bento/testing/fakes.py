"""Fake implementations for testing Bento applications.

Provides in-memory test doubles for:
- UnitOfWork
- Repository
- IdempotencyStore
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

AR = TypeVar("AR")
ID = TypeVar("ID")


class InMemoryRepository[AR, ID]:
    """In-memory repository for testing.

    Stores entities in a dictionary keyed by ID.

    Example:
        ```python
        repo = InMemoryRepository[Order, str]()
        await repo.save(order)
        found = await repo.get(order.id)
        ```
    """

    def __init__(self):
        self._store: dict[Any, AR] = {}
        self._id_extractor: Callable[[AR], Any] | None = None

    def set_id_extractor(self, extractor: Callable[[AR], Any]) -> None:
        """Set function to extract ID from entity."""
        self._id_extractor = extractor

    def _get_id(self, entity: AR) -> Any:
        """Extract ID from entity."""
        if self._id_extractor:
            return self._id_extractor(entity)
        # Try common patterns
        for attr in ["id", "entity_id", "aggregate_id"]:
            if hasattr(entity, attr):
                val = getattr(entity, attr)
                # Handle value objects with .value
                return getattr(val, "value", val)
        raise ValueError("Cannot determine entity ID. Set id_extractor.")

    async def get(self, entity_id: ID) -> AR | None:
        """Get entity by ID."""
        key = getattr(entity_id, "value", entity_id)
        return self._store.get(key)

    async def find_by_id(self, entity_id: ID) -> AR | None:
        """Alias for get()."""
        return await self.get(entity_id)

    async def save(self, entity: AR) -> None:
        """Save entity."""
        key = self._get_id(entity)
        self._store[key] = entity

    async def delete(self, entity: AR) -> None:
        """Delete entity."""
        key = self._get_id(entity)
        self._store.pop(key, None)

    async def find_all(self, spec: Any = None) -> list[AR]:
        """Find all entities."""
        return list(self._store.values())

    async def exists(self, entity_id: ID) -> bool:
        """Check if entity exists."""
        key = getattr(entity_id, "value", entity_id)
        return key in self._store

    async def count(self) -> int:
        """Count entities."""
        return len(self._store)

    def clear(self) -> None:
        """Clear all stored entities."""
        self._store.clear()


class FakeIdempotencyStore:
    """Fake idempotency store for testing.

    Stores responses in memory.

    Example:
        ```python
        store = FakeIdempotencyStore()
        await store.store_response("key-1", {"id": "123"}, request_hash="abc")
        cached = await store.get_response("key-1")
        ```
    """

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    async def get_response(self, key: str) -> Any | None:
        """Get cached response."""
        data = self._store.get(key)
        if data is None:
            return None
        # Return mock object with expected attributes
        return type(
            "CachedResponse",
            (),
            {
                "request_hash": data["request_hash"],
                "response_body": data["response_body"],
            },
        )()

    async def store_response(
        self,
        key: str,
        response: Any,
        *,
        request_hash: str = "",
    ) -> None:
        """Store response."""
        self._store[key] = {
            "request_hash": request_hash,
            "response_body": response,
        }

    def clear(self) -> None:
        """Clear all stored responses."""
        self._store.clear()


class FakeUnitOfWork:
    """Fake Unit of Work for testing.

    Provides in-memory repositories and idempotency store.

    Example:
        ```python
        uow = FakeUnitOfWork()

        # Register repository for an aggregate type
        uow.register_repository(Order, InMemoryRepository)

        # Use in handler
        handler = CreateOrderHandler(uow)
        result = await handler.execute(command)
        ```
    """

    def __init__(self):
        self._repositories: dict[type, Any] = {}
        self._tracked: list[Any] = []
        self._tenant_id: str | None = None
        self._committed = False
        self.idempotency = FakeIdempotencyStore()

    def register_repository(
        self,
        aggregate_type: type[AR],
        repo_factory: Callable[..., Any] | None = None,
    ) -> None:
        """Register a repository for an aggregate type."""
        if repo_factory is None:

            def default_factory() -> InMemoryRepository:
                return InMemoryRepository()

            repo_factory = default_factory

        if callable(repo_factory) and not isinstance(repo_factory, type):
            self._repositories[aggregate_type] = repo_factory()
        else:
            self._repositories[aggregate_type] = repo_factory()

    def repository(self, aggregate_type: type) -> Any:
        """Get repository for aggregate type."""
        if aggregate_type not in self._repositories:
            # Auto-create InMemoryRepository
            self._repositories[aggregate_type] = InMemoryRepository()
        return self._repositories[aggregate_type]

    def track(self, aggregate: Any) -> None:
        """Track aggregate for event collection."""
        self._tracked.append(aggregate)

    def set_tenant_id(self, tenant_id: str) -> None:
        """Set tenant ID for multi-tenant operations."""
        self._tenant_id = tenant_id

    async def commit(self) -> None:
        """Commit (no-op for fake)."""
        self._committed = True

    async def rollback(self) -> None:
        """Rollback (no-op for fake)."""
        pass

    async def __aenter__(self) -> FakeUnitOfWork:
        """Enter context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        if exc_type is None and not self._committed:
            await self.commit()

    @property
    def tracked_aggregates(self) -> list[Any]:
        """Get tracked aggregates."""
        return self._tracked

    @property
    def was_committed(self) -> bool:
        """Check if commit was called."""
        return self._committed

    def reset(self) -> None:
        """Reset state for next test."""
        self._tracked.clear()
        self._committed = False
        self._tenant_id = None
        for repo in self._repositories.values():
            if hasattr(repo, "clear"):
                repo.clear()
        self.idempotency.clear()
