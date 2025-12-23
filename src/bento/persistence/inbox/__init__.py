"""Inbox Pattern implementation for reliable message consumption.

This module implements the Inbox pattern for ensuring exactly-once message
processing in event-driven architectures.

Pattern:
1. Before processing a message, check if its ID exists in the inbox table
2. If exists, skip processing (already processed)
3. If not exists, process the message and record it in the inbox table
4. Both steps happen in the same transaction

This is the counterpart to the Outbox pattern:
- Outbox: Ensures exactly-once sending
- Inbox: Ensures exactly-once processing

Example:
    ```python
    from bento.persistence.inbox import InboxRecord, SqlAlchemyInbox

    inbox = SqlAlchemyInbox(session)

    async def handle_message(message_id: str, payload: dict):
        # Check if already processed
        if await inbox.is_processed(message_id):
            return  # Skip duplicate

        # Process message
        await process_business_logic(payload)

        # Mark as processed (in same transaction)
        await inbox.mark_processed(message_id, "OrderCreated", payload)
        await session.commit()
    ```
"""

from bento.persistence.inbox.record import InboxRecord, SqlAlchemyInbox

__all__ = [
    "InboxRecord",
    "SqlAlchemyInbox",
]
