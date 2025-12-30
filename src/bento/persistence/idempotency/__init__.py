"""Idempotency Pattern implementation for command deduplication.

This module implements the Idempotency pattern for ensuring exactly-once
command execution in distributed systems.

Pattern:
1. Client sends request with Idempotency-Key header
2. Before processing, check if key exists in idempotency store
3. If exists, return cached response
4. If not exists, process command, store result, return response

This is different from Inbox pattern:
- Inbox: Message-level deduplication (event_id based)
- Idempotency: Command-level deduplication (client-provided key)

Example:
    ```python
    from bento.persistence.idempotency import IdempotencyRecord, SqlAlchemyIdempotency

    idempotency = SqlAlchemyIdempotency(session)

    async def handle_create_order(idempotency_key: str, command: CreateOrderCommand):
        # Check if already processed
        cached = await idempotency.get_response(idempotency_key)
        if cached:
            return cached  # Return cached response

        # Process command
        result = await process_create_order(command)

        # Store response for future duplicate requests
        await idempotency.store_response(
            idempotency_key=idempotency_key,
            operation="CreateOrder",
            request_hash=hash(command),
            response=result.to_dict(),
            status_code=201,
        )
        await session.commit()

        return result
    ```
"""

from bento.persistence.idempotency.record import (
    IdempotencyConflictException,
    IdempotencyRecord,
    SqlAlchemyIdempotency,
)

__all__ = [
    "IdempotencyRecord",
    "IdempotencyConflictException",
    "SqlAlchemyIdempotency",
]
