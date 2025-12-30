"""Idempotency Protocol - Interface for command idempotency.

This module defines the Idempotency protocol that abstracts the idempotency
storage implementation, following the hexagonal architecture pattern.

Simplified Design (no PENDING state):
1. Check get_response() for cached result
2. If None, execute command
3. Call store_response() to cache result
4. Concurrent requests may both execute, but only one succeeds in storing
"""

from typing import Any, Protocol


class IdempotencyStore(Protocol):
    """Protocol for idempotency operations.

    The Idempotency pattern ensures exactly-once command execution
    by caching command results keyed by client-provided idempotency keys.

    Simplified design without PENDING state:
    - get_response(): Check for cached result
    - store_response(): Store result (uses upsert for concurrency)
    - No locking needed - concurrent requests handled by database constraints
    """

    async def get_response(self, idempotency_key: str) -> Any | None:
        """Get cached response for an idempotency key.

        Args:
            idempotency_key: Client-provided unique key

        Returns:
            Cached record if found and valid, None otherwise
        """
        ...

    async def is_processing(self, idempotency_key: str) -> bool:
        """Check if a request is currently being processed.

        Note: Simplified implementation always returns False
        since we don't track PENDING state.

        Args:
            idempotency_key: The idempotency key to check

        Returns:
            Always False (no PENDING state)
        """
        ...

    async def lock(
        self,
        idempotency_key: str,
        operation: str,
        request_hash: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Any | None:
        """Check if idempotency key already exists.

        Simplified design: no locking, just check for existing record.

        Args:
            idempotency_key: Client-provided unique key
            operation: Name of the operation
            request_hash: Optional hash of request for conflict detection
            ttl_seconds: Not used in simplified design

        Returns:
            Existing record if found, None otherwise
        """
        ...

    async def store_response(
        self,
        idempotency_key: str,
        response: dict[str, Any],
        status_code: int = 200,
        operation: str = "",
        request_hash: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Any:
        """Store the response for an idempotency key.

        Creates a COMPLETED record directly (no PENDING needed).
        Uses upsert for concurrent insert handling.

        Args:
            idempotency_key: The idempotency key
            response: Response data to cache
            status_code: HTTP status code
            operation: Name of the operation
            request_hash: Optional hash of request
            ttl_seconds: Time-to-live in seconds

        Returns:
            Created record
        """
        ...

    async def mark_failed(self, idempotency_key: str) -> None:
        """Mark a request as failed (allows retry).

        Args:
            idempotency_key: The idempotency key
        """
        ...
