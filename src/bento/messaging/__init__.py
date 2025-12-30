"""Messaging module for Bento framework.

Provides protocols and utilities for event-driven messaging:
- Outbox: Ensures exactly-once sending (transactional outbox pattern)
- Inbox: Ensures exactly-once processing (message deduplication)
- IdempotencyStore: Ensures exactly-once command execution
- MessageEnvelope: Standardized message wrapper with tracing
"""

from bento.messaging.envelope import MessageEnvelope
from bento.messaging.idempotency import IdempotencyStore
from bento.messaging.inbox import Inbox
from bento.messaging.outbox import Outbox

__all__ = [
    "Inbox",
    "IdempotencyStore",
    "Outbox",
    "MessageEnvelope",
]
