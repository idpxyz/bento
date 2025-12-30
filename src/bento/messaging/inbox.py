"""Inbox Protocol - Interface for message deduplication.

This module defines the Inbox protocol that abstracts the inbox storage
implementation, following the hexagonal architecture pattern.
"""

from typing import Any, Protocol


class Inbox(Protocol):
    """Protocol for inbox operations (message deduplication).

    The Inbox pattern ensures exactly-once processing of messages
    by tracking which message IDs have already been processed.

    Implementations should be transactional - the mark_processed
    operation should be committed in the same transaction as
    the business logic that processes the message.
    """

    async def is_processed(self, message_id: str) -> bool:
        """Check if a message has already been processed.

        Args:
            message_id: Unique identifier of the message

        Returns:
            True if already processed, False otherwise
        """
        ...

    async def mark_processed(
        self,
        message_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        source: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Any:
        """Mark a message as processed.

        This should be called after successfully processing a message,
        within the same database transaction.

        Args:
            message_id: Unique message identifier
            event_type: Type of event that was processed
            payload: Optional payload (for audit/debugging)
            source: Optional source service
            metadata: Optional additional metadata
        """
        ...
